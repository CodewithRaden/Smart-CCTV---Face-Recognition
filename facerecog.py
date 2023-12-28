import face_recognition
import cv2
import os


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


video_capture = cv2.VideoCapture(0)
video_capture.set(3, 640)
video_capture.set(4, 480)

font = cv2.FONT_HERSHEY_DUPLEX

frame_count = 0

while True:
    # Capture every second frame to reduce processing load
    if frame_count % 2 == 0:
        ret, frame = video_capture.read()

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

        cv2.imshow('Video', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    frame_count += 1

video_capture.release()
cv2.destroyAllWindows()
