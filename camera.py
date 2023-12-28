import cv2
import threading
import os
from datetime import datetime

class RecordingThread(threading.Thread):
    def __init__(self, name, camera, output_folder):
        threading.Thread.__init__(self)
        self.name = name
        self.isRunning = True

        self.cap = camera
        self.output_folder = output_folder
        self.out = self.initialize_video_writer()

    def initialize_video_writer(self):
        try:
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}.avi"
            filepath = os.path.join(self.output_folder, filename)

            # Get the original frame width and height
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            return cv2.VideoWriter(filepath, fourcc, 20.0, (width, height))
        except Exception as e:
            print(f"Error initializing video writer: {e}")
            return None

    def run(self):
        while self.isRunning:
            ret, frame = self.cap.read()
            if ret:
                self.out.write(frame)

        # Release the video writer when done
        self.out.release()

    def stop(self):
        self.isRunning = False
        self.recordingThread.join(timeout=5)  # Wait for the thread to finish

    def __del__(self):
        self.out.release()


class VideoCamera(object):
    def __init__(self, output_folder):
        # Open a camera
        self.cap = cv2.VideoCapture(0)

        # Initialize video recording environment
        self.is_record = False
        self.recordingThread = None
        self.output_folder = output_folder

    def __del__(self):
        self.cap.release()

    def get_frame(self):
        ret, frame = self.cap.read()

        if ret:
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            return jpeg.tobytes()
        else:
            return None

    def start_record(self):
        self.is_record = True
        self.recordingThread = RecordingThread("Video Recording Thread", self.cap, self.output_folder)
        self.recordingThread.start()

    def stop_record(self):
        self.is_record = False

        if self.recordingThread is not None:
            self.recordingThread.stop()

            # Ensure the recording thread has finished before continuing
            try:
                self.recordingThread.join(timeout=5)
            except RuntimeError:
                pass  # Ignore RuntimeError if the thread has already terminated