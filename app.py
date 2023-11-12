from flask import Flask, render_template,Response,request, redirect, url_for, session
from flask_bcrypt import Bcrypt 
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import cv2
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
    
# @app.route('/history')
# def history():
#     if 'loggedin' in session:
#         events = get_motion_events()

#         return render_template('recorded_data.html', events=events)
#     else:
#         return redirect(url_for('login')) 

if __name__ == "__main__":
    app.run(debug=True)