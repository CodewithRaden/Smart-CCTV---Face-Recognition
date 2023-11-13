import cv2
import numpy as np

# Initialize the camera
cap = cv2.VideoCapture(0)

# Load the face detection classifier
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Initialize variables
skip = 0
face_data = []
dataset_path = "./face_data/"
file_name = input("Enter the name of the person: ")

while True:
    # Capture a frame from the camera
    ret, frame = cap.read()

    # Convert the frame to grayscale for face detection
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if not ret:
        continue

    # Detect faces in the grayscale frame
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

    if len(faces) == 0:
        continue

    k = 0  # Start counting faces from 0

    for face in faces:
        x, y, w, h = face

        # Extract the face region with some margin
        offset = 10
        face_offset = frame[y - offset : y + h + offset, x - offset : x + w + offset]

        # Resize the extracted face region to a consistent size
        face_selection = cv2.resize(face_offset, (100, 100))

        if skip % 10 == 0:
            # Append the face to the training data
            face_data.append(face_selection)
            print(f"Face {k} added to dataset.")
        k += 1

        # Display the captured face with a bounding box
        cv2.imshow(f"Face {k}", face_selection)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Check if the 'q' key is pressed to exit the capture loop
    key_pressed = cv2.waitKey(1) & 0xFF
    if key_pressed == ord('q'):
        break

# Convert the collected face data to a NumPy array
face_data = np.array(face_data)

# Flatten the face data for storage
face_data = face_data.reshape((face_data.shape[0], -1))

# Display the number of faces collected
print(f"Dataset contains {len(face_data)} faces.")

# Save the collected face data to a file
np.save(dataset_path + file_name, face_data)
print(f"Dataset saved at: {dataset_path + file_name + '.npy'}")

# Release the camera and close OpenCV windows
cap.release()
cv2.destroyAllWindows()
