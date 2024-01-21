from flask import Flask, render_template, Response, request, redirect, url_for, session,jsonify,send_file,flash
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
import MySQLdb.cursors
import cv2
import os
import threading
import face_recognition
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO
# import RPi.GPIO as GPIO
from threading import Timer


app = Flask(__name__)
bcrypt = Bcrypt(app)
socketio = SocketIO(app)

app.secret_key = 'alter'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '' #ubah sesuai device / hardware (rasberi : "admin")
app.config['MYSQL_DB'] = 'muak_db'

mysql = MySQL(app)

class Admin: # clas admin dengan nama,email dan password
    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

    def save_to_db(self): # menyimpan data admin ke database setelah meng-hash password.
        hashed_password = bcrypt.generate_password_hash(self.password).decode('utf-8')
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO user (name, email, password) VALUES (%s, %s, %s)',
                           (self.name, self.email, hashed_password))
            mysql.connection.commit()
        except Exception as error:
            print(f"Error saving data to database: {error}")
        finally:
            cursor.close()


class Database: # method untuk cek data admin yg ada didalam database 
    @staticmethod
    def check_admin(email, password):
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        admin = cursor.fetchone()

        if admin and bcrypt.check_password_hash(admin['password'], password):
            return admin
        else:
            return None
            

class Camera: # instance satu kamera dan method untuk instance camera
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Camera, cls).__new__(cls)
            cls._instance.camera = cv2.VideoCapture(0) #backend =  cv2.CAP_V4L2, cv2.CAP_GSTREAMER
            width = 256 #cam resolusi
            height = 256 #cam resolusi
            cls._instance.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cls._instance.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        return cls._instance

    def get_camera(self):
        return self.camera

class RecordingThread(threading.Thread): # thread (eksekusi pararel) untuk video record dan video writer
    def __init__(self, camera, output_folder):
        threading.Thread.__init__(self)
        self.isRunning = True
        self.cap = camera
        self.output_folder = output_folder
        self.out = self.video_writer()

    def video_writer(self):
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.mp4"
            filepath = os.path.join(self.output_folder, filename)

            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
            return cv2.VideoWriter(filepath, fourcc, 20.0, (width, height))
        except Exception as error:
            print(f"Error Writing Video Data: {error}")
            return None

    def run(self): #overrun metod run di thread class
        while self.isRunning:
            ret, frame = self.cap.read()
            if ret:
                self.out.write(frame)

        self.out.release()

    def stop(self):
        self.isRunning = False
        self.join(timeout=5)

    def __del__(self):
        self.out.release()
        self.out = None



class VideoCamera(object):
    def __init__(self, output_folder):
        self.camera_single = Camera()
        self.is_record = False
        self.recording_thread = None
        self.output_folder = output_folder
        self.lock = threading.Lock()

    def __del__(self):
        pass

    def get_frame(self):
        ret, frame = self.camera_single.get_camera().read()

        if ret:
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            return jpeg.tobytes()
        else:
            return None

    def start_record(self):
        with self.lock:
            if not self.is_record:
                self.is_record = True
                self.recording_thread = RecordingThread(self.camera_single.get_camera(), self.output_folder) #instace Recording Class
                self.recording_thread.start()

    def stop_record(self):
        with self.lock: # with lock untuk memastikan atomicity (semuanya selesai)
            if self.is_record:
                self.is_record = False

                if self.recording_thread is not None:
                    self.recording_thread.stop()

                    try:
                        self.recording_thread.join(timeout=5)
                    except RuntimeError:
                        pass

                    del self.recording_thread

video_camera = VideoCamera("static/recorded_videos") # instance VideoCamera class

def star_recorded_video():
    print("Recording started!")

def save_recorded_video():
    print("Recording saved!")


def before_request():
    allowed_routes = ['login', 'register']

    if 'loggedin' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))


def load_known_faces(directory):
    known_images = []
    known_names = []
    try:
        for filename in os.listdir(directory):
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                path = os.path.join(directory, filename)
                image = face_recognition.load_image_file(path)
                encoding = face_recognition.face_encodings(image)
                if encoding:
                    known_images.append(encoding[0])
                    known_names.append(os.path.splitext(filename)[0])
    except Exception as error:
        print(f"Error loading known faces: {error}")

    return known_images, known_names


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
    
    
camera_single = Camera() # instace class camera for camera use
camera = camera_single.get_camera()
font = cv2.FONT_HERSHEY_DUPLEX

@app.route('/facerecognition')
def facerecognition():
    if 'loggedin' in session:
        return render_template('facerecognition.html')
    else:
        return redirect(url_for('login'))
    
def generate_frames(): # buat streaming video tanpa face recog
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def gen_frames_face(): # buat streaming video with face recog
    while True:
        ret, frame = camera.read()

        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)

            name = "Unknown"

            for i in range(len(matches)):
                if matches[i]:
                    name = known_names[i]
                    break

            if name == "Unknown":
                socketio.emit('notification', {'message': 'Unknown face detected'}, namespace='/facerecognition')
                break

            cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 255), 2)
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, (255, 0, 0), 1)

        _, jpeg = cv2.imencode('.jpg', frame)
        data = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + data + b'\r\n\r\n')

@app.route('/videosource')
def video():
    if 'loggedin' in session:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for('login'))
    
@app.route('/video_feed_face')
def video_feed_face(): #response video with face recog
    if 'loggedin' in session:
        return Response(gen_frames_face(),mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return redirect(url_for('login'))
    

        
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
    

    
@app.route('/start_recording')
def start_recording():
    video_camera.start_record()
    star_recorded_video()
    return jsonify({'status': 'Recording started'})

@app.route('/stop_recording')
def stop_recording():
    video_camera.stop_record()
    save_recorded_video()
    return jsonify({'status': 'Recording stopped and saved'})


@app.route('/recorded_videos')
def recorded_videos():
    if 'loggedin' in session:
        video_folder = "static/recorded_videos"
        video_files = [f for f in os.listdir(video_folder) if f.endswith(".avi") or f.endswith(".mp4")]
        return render_template('recorded_videos.html', video_files=video_files)
    else:
        return redirect(url_for('login'))
    

@app.route('/play_video/<filename>') 
def play_video(filename):
    videos_folder = 'static/recorded_videos'
    video_path = os.path.join(videos_folder, filename)
    return send_file(video_path, mimetype='video/avi', as_attachment=False)


@app.route('/add_face', methods=['GET', 'POST'])
def add_face():
    if request.method == 'POST':
        if 'face_image' in request.files:
            face_image = request.files['face_image']
            if face_image.filename != '':
                filename = secure_filename(face_image.filename)
                face_image_path = os.path.join('faces', filename)
                face_image.save(face_image_path)

                encoding = update_face_model(face_image_path)

                if encoding is not None:
                    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                    cursor.execute('INSERT INTO face_data (face_encoding, file_name) VALUES (%s, %s)',
                                   (str(encoding), filename))
                    mysql.connection.commit()

                    flash('Success Add Face Data')
                    return redirect(url_for('add_face'))
                else:
                    flash('Error updating face model. Please make sure the image contains a face.')

    return render_template('add_face.html')

def update_face_model(face_image_path):
    try:
        image = face_recognition.load_image_file(face_image_path)
        encoding = face_recognition.face_encodings(image)
        if encoding and len(encoding) > 0:
            return encoding[0]
        else:
            return None
    except Exception as error:
        print(f"Error updating face model: {error}")
        return None


@socketio.on('connect', namespace='/facerecognition')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect', namespace='/facerecognition')
def handle_disconnect():
    print('Client disconnected')
    
    
# PIR_PIN = 4
# GPIO.setmode(GPIO.BCM)
# GPIO.setup(PIR_PIN, GPIO.IN)


@app.route('/motion_detection')
def motion_detection():
    if 'loggedin' in session:
        return render_template('motion_detection.html')
    else:
        return redirect(url_for('login'))
        


motion_detection_active = False
start_recording_flag = False

@app.route('/motion_detection_toggle')
def motion_detection_toggle():
    global motion_detection_active
    motion_detection_active = not motion_detection_active
    return jsonify({'status': 'Motion detection toggled'})


def stop_recording_and_close_camera():
    video_camera.stop_record()
    save_recorded_video()
    socketio.emit('camera_closed', namespace='/facerecognition')

@app.route('/automation_mode')
def automation_mode():
    global motion_detection_active
    motion_detection_active = True
    return render_template('motion_detection.html')  

def check_unknown_face():
    # Use face recognition library to check for unknown faces
    ret, frame = camera.read()
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.5)

        if not any(matches):
            return True  # Unknown face detected

    return False

# def motion_detection_thread():
    motion_detected = False
    unknown_face_detected = False
    global start_recording_flag

    while True:
        if motion_detection_active and GPIO.input(PIR_PIN):
            # Motion detected
            motion_detected = True
            socketio.emit('motion_detected', namespace='/facerecognition')

            # Check for unknown face
            if check_unknown_face():
                unknown_face_detected = True
                start_recording_flag = True
        else:
            # No motion
            motion_detected = False
            unknown_face_detected = False
            start_recording_flag = False
            socketio.emit('no_motion_detected', namespace='/facerecognition')

        # Check if recording should be started
        if start_recording_flag and unknown_face_detected:
            video_camera.start_record()
            start_recording_flag = False

            # Set a timer to stop recording after 10 seconds
            recording_timer = Timer(10, stop_recording_and_close_camera)
            recording_timer.start()

        # Send motion status to the frontend
        socketio.emit('motion_status', {'motion_detected': motion_detected}, namespace='/facerecognition')

        # Reset unknown_face_detected for the next iteration
        unknown_face_detected = False

@app.route('/go_back')
def go_back():
    global motion_detection_active
    motion_detection_active = False
    return redirect(url_for('home')) 

# motion_thread = threading.Thread(target=motion_detection_thread)
# motion_thread.start()
  
if __name__ == '__main__':
    app.run(debug=True)
