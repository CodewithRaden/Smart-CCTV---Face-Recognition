from flask import Flask, render_template,Response,request, redirect, url_for, session
from flask_bcrypt import Bcrypt 
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import cv2
import numpy as np
import os
# from threading import Thread
# from motion_detection import motion_detection,get_motion_events
  
  
app = Flask(__name__)
bcrypt = Bcrypt(app)  
  
app.secret_key = 'pantek'
  
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'muak_db'
  
mysql = MySQL(app)

def before_request():
    allowed_routes = ['login', 'register']

    
    if 'loggedin' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))
  
@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['userid'] = user['userid']
            session['name'] = user['name']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return render_template('home.html', message=message)
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

        
        if admin_key != 'kel1pbl': #Ini key admin
            message = 'Invalid admin key!'
            return render_template('register.html', message=message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()

        if account:
            message = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            message = 'Invalid email address!'
        elif not user_name or not password or not email:
            message = 'Please fill out the form!'
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            cursor.execute('INSERT INTO user (name, email, password) VALUES (%s, %s, %s)', (user_name, email, hashed_password))
            mysql.connection.commit()
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

def load_face_data(dataset_path):
    face_data = []
    labels = []
    names = {}
    class_id = 0

    for fx in os.listdir(dataset_path):
        if fx.endswith('.npy'):
            names[class_id] = fx[:-4]
            data_item = np.load(os.path.join(dataset_path, fx))
            face_data.append(data_item)
            target = class_id * np.ones((data_item.shape[0],))
            labels.extend(target.reshape(-1, 1))
            class_id += 1

    face_dataset = np.concatenate(face_data, axis=0)
    face_labels = np.array(labels)
    
    return face_dataset, face_labels, names


# Function to compute distance between two vectors
def distance(v1, v2):
    return np.sqrt(((v1 - v2) ** 2).sum())

# Function for k-nearest neighbors algorithm
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

# Function to detect and recognize faces
def detect_and_recognize_faces(frame, face_cascade, knn, names):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)

    for face in faces:
        x, y, w, h = face
        face_section = frame[y:y+h, x:x+w]
        face_section = cv2.resize(face_section, (100, 100))
        face_data = face_section.reshape(1, -1)

        result, _ = knn.findNearest(np.float32(face_data), k=5)
        label = int(result[0][0])
        predicted_name = names[label]

        cv2.putText(frame, predicted_name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)

    return frame

dataset_path = "face_data/"
face_data, face_labels, names = load_face_data(dataset_path)

trainset = np.concatenate((face_data, face_labels), axis=1)
knn = cv2.ml.KNearest_create()
knn.train(trainset.astype(np.float32), cv2.ml.ROW_SAMPLE, face_labels.astype(np.float32))



face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml')

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
        return render_template('home.html')
     else:
        return redirect(url_for('login'))
        
@app.route('/livestream')
def live():
    if 'loggedin' in session:
        # motion_thread = Thread(target=motion_detection, args=('record_data/',))
        # motion_thread.start()
        return render_template('livestream.html')
    else:
        return redirect(url_for('login'))
        
@app.route('/videosource')
def video():
    if 'loggedin' in session:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for('login'))
    
@app.route('/facerecognition')
def facerecognition():
    return render_template('facerecognition.html')

def generate_frames_with_face_recognition():
    while True:
        success, frame = camera.read()
        if not success:
            break

        # Perform face recognition on the frame
        frame = detect_and_recognize_faces(frame, face_cascade, knn, names)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames_with_face_recognition(), mimetype='multipart/x-mixed-replace; boundary=frame')

    
# @app.route('/history')
# def history():
#     if 'loggedin' in session:
#         events = get_motion_events()

#         return render_template('recorded_data.html', events=events)
#     else:
#         return redirect(url_for('login')) 

if __name__ == "__main__":
    app.run(debug=True)