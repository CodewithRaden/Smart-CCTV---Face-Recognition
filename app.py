from flask import Flask, render_template, Response, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import MySQLdb.cursors
import cv2
import numpy as np
import os
import face_recognition


app = Flask(__name__)
bcrypt = Bcrypt(app)

app.secret_key = 'alter'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'muak_db'

mysql = MySQL(app)

class Admin:
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

    def save_to_db(self):
        hashed_password = bcrypt.generate_password_hash(self.password).decode('utf-8')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO user (name, email, password) VALUES (%s, %s, %s)',
                       (self.name, self.email, hashed_password))
        mysql.connection.commit()


class Database:
    @staticmethod
    def check_admin(email, password):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        admin = cursor.fetchone()

        if admin and bcrypt.check_password_hash(admin['password'], password):
            return admin
        else:
            return None


def before_request():
    allowed_routes = ['login', 'register']

    if 'loggedin' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))


def load_known_faces(directory):
    known_images = []
    known_names = []

    for filename in os.listdir(directory):
        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            path = os.path.join(directory, filename)
            image = face_recognition.load_image_file(path)
            encoding = face_recognition.face_encodings(image)
            if encoding:
                known_images.append(encoding[0])
                known_names.append(os.path.splitext(filename)[0])

    return known_images, known_names

# Specify the directory containing face images
faces_directory = "faces"
known_encodings, known_names = load_known_faces(faces_directory)


@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']

        user = Database.check_admin(email, password)
        if user:
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return render_template('index.html', message=message)
        else:
            message = 'Email or Password Invalid!'
    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('email', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        user_name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        admin_key = request.form['admin_key']

        if admin_key != 'kel1pbl':  # Ini key admin
            message = 'Invalid admin key!'
            return render_template('register.html', message=message)

        existing_user = Database.check_admin(email, password)
        if existing_user:
            message = 'Account already exists!'
        elif not user_name or not password or not email:
            message = 'Please fill out the form!'
        else:
            new_admin = Admin(user_name, email, password)
            new_admin.save_to_db()
            message = 'You have successfully registered!'

    elif request.method == 'POST':
        message = 'Please fill out the form!'

    return render_template('register.html', message=message)


@app.route('/profile')
def profile():
    if 'loggedin' in session:
        user_id = session['userid']
        user_name = session['name']
        user_email = session['email']
        return render_template('profile.html', user_id=user_id, user_name=user_name, user_email=user_email)
    else:
        return redirect(url_for('login'))
    
    
camera = cv2.VideoCapture(0)
#Set the video capture properties
new_width = 256
new_height = 256
camera.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)

font = cv2.FONT_HERSHEY_DUPLEX

@app.route('/facerecognition')
def facerecognition():
    if 'loggedin' in session:
        return render_template('facerecognition.html')
    else:
        return redirect(url_for('login'))

def gen_frames_face():
    while True:
        ret, frame = camera.read()

        # Find all face locations and face encodings in the current frame
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            # Check if the face matches any of the known people
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)

            name = "Unknown"

            for i in range(len(matches)):
                if matches[i]:
                    name = known_names[i]
                    break

            cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 255), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (0, 0, 255), 1)

        _, jpeg = cv2.imencode('.jpg', frame)
        data = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n\r\n')


@app.route('/video_feed_face')
def video_feed_face():
    return Response(gen_frames_face(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
@app.route('/home')
def home():
     if 'loggedin' in session:
        return render_template('index.html')
     else:
        return redirect(url_for('login'))
        
@app.route('/livestream')
def live():
    if 'loggedin' in session:
        return render_template('livestream.html')
    else:
        return redirect(url_for('login'))
        
@app.route('/videosource')
def video():
    if 'loggedin' in session:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for('login'))

@app.route('/manual')
def manual():
    if 'loggedin' in session:
        return render_template("manual.html")
    else:
        return redirect(url_for('login'))
    
@app.route('/coming')
def coming():
    if 'loggedin' in session:
        return render_template('Comingsoon.html')
    else:
        return redirect(url_for('login'))


@app.route('/coming_record')
def coming_record():
    if 'loggedin' in session:
        return render_template('Comingsoon_record.html')
    else:
        return redirect(url_for('login'))
    

if __name__ == '__main__':
    app.run(debug=True)
