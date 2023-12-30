from flask import Flask, render_template, Response
import cv2
import os
from datetime import datetime

app = Flask(__name__)

output_folder = "recorded_videos"
os.makedirs(output_folder, exist_ok=True)

cap = None
writer = None
recording = False

def generate_frames():
    global cap, writer, recording
    while recording:
        ret, frame = cap.read()
        if ret:
            writer.write(frame)
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
        else:
            break


@app.route('/')
def index():
    return render_template('indexx.html')

def start_recording():
    global cap, writer, recording
    cap = cv2.VideoCapture(0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file_path = os.path.join(output_folder, f"video_{current_datetime}.mp4")
    writer = cv2.VideoWriter(output_file_path, cv2.VideoWriter_fourcc(*'MP4'), 20, (width, height))
    recording = True

def stop_recording():
    global cap, writer, recording
    recording = False
    cap.release()
    writer.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/record', methods=['POST'])
def record():
    start_recording()
    return "Recording started"

@app.route('/stop', methods=['POST'])
def stop():
    stop_recording()
    return "Recording stopped"

if __name__ == '__main__':
    app.run(debug=True)
