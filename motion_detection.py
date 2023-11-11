import cv2
import os
import mysql.connector
from datetime import datetime

def motion_detection(output_folder):
    cap = cv2.VideoCapture(0)

    motion_threshold = 1000  # Adjust as needed
    motion_detected = False
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = None

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='muak_db'
    )
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motion_events (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255),
            date DATE,
            time TIME
        )
    ''')
    conn.commit()

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if not motion_detected:
            first_frame = gray
            motion_detected = True
            continue

        frame_delta = cv2.absdiff(first_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            if out is not None:
                out.release()
                out = None
                motion_detected = False
        else:
            if out is None:
                today_date = datetime.today().strftime('%Y-%m-%d')
                timestamp = datetime.now().strftime('%H:%M:%S')
                filename = f'motion_detected_{today_date}_{timestamp}.avi'
                output_path = os.path.join(output_folder, filename)
                out = cv2.VideoWriter(output_path, fourcc, 20.0, (frame.shape[1], frame.shape[0]))

                cursor.execute("INSERT INTO motion_events (filename, date, time) VALUES (%s, %s, %s)",
                               (filename, today_date, timestamp))
                conn.commit()

            for contour in contours:
                if cv2.contourArea(contour) > motion_threshold:
                    out.write(frame)

    cursor.close()
    conn.close()

    cap.release()
    if out is not None:
        out.release()
    cv2.destroyAllWindows()

def get_motion_events():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='muak_db'
        )

        if conn.is_connected():
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM motion_events ORDER BY id DESC LIMIT 10")  # Limit to the last 10 events
            events = cursor.fetchall()

            cursor.close()
            conn.close()

            return events

    except Exception as e:
        print("Error:", e)
        return []
    
def get_video_filenames():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='muak_db'
        )

        if conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM motion_events ORDER BY id DESC LIMIT 10")  # Limit to the last 10 events
            filenames = cursor.fetchall()

            cursor.close()
            conn.close()

            return [filename[0] for filename in filenames]

    except Exception as e:
        print("Error:", e)
        return []