from flask import Flask, render_template, Response, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import MySQLdb.cursors
import cv2
import numpy as np
import os

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


camera = cv2.VideoCapture(2)
# Set the video capture properties
new_width = 640
new_height = 480
camera.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)

face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_alt.xml")
dataset_path = "face_data/"
face_data = []
labels = []
class_id = 0
names = {}

for fx in os.listdir(dataset_path):
    if fx.endswith('.npy'):
        names[class_id] = fx[:-4]
        data_item = np.load(dataset_path + fx)
        face_data.append(data_item)

        target = class_id * np.ones((data_item.shape[0],))
        class_id += 1
        labels.append(target)

face_dataset = np.concatenate(face_data, axis=0)
face_labels = np.concatenate(labels, axis=0).reshape((-1, 1))

trainset = np.concatenate((face_dataset, face_labels), axis=1)

def knn(train, test, k=5):
    dist = []
    
    for i in range(train.shape[0]):
        ix = train[i, :-1]
        iy = train[i, -1]

        d = distance(test, ix)
        dist.append([d, iy])
    
    dk = sorted(dist, key=lambda x: x[0])[:k]
   
    labels = np.array(dk)[:, -1]
    output = np.unique(labels, return_counts=True)
    
    index = np.argmax(output[1])
    return output[0][index]

def distance(v1, v2):
    return np.sqrt(((v1 - v2) ** 2).sum())

@app.route('/facerecognition')
def facerecognition():
    if 'loggedin' in session:
        return render_template('facerecognition.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/video_feed_face')
def video_feed_face():
    return Response(generate_frames_face(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames_face():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5)

            for face in faces:
                x, y, w, h = face
                offset = 5
                face_section = frame[y - offset : y + h + offset, x - offset : x + w + offset]
                face_section = cv2.resize(face_section, (100, 100))
                out = knn(trainset, face_section.flatten())

                cv2.putText(frame, names[int(out)], (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


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

if __name__ == "__main__":
    app.run(debug=True)