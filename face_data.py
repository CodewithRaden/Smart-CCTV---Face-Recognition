import cv2
import numpy as np


cap = cv2.VideoCapture(2)

new_width = 640
new_height = 480

# Set the video capture properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)

# Load klasifikasi deteksi wajah
face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# Inisialisasi variabel
skip = 0
face_data = []
dataset_path = "./face_data/"
file_name = input("Enter the name of the person: ")

while True:
    # capture frame camera
    ret, frame = cap.read()

    # Convert ke grayscale biar gak berat
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if not ret:
        continue

    # detect muka di scale gray
    faces = face_cascade.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

    if len(faces) == 0:
        continue

    k = 0  # buat nanti penambahan data muka

    for face in faces:
        x, y, w, h = face

        # mengambil data wajah
        offset = 10
        face_offset = frame[y - offset : y + h + offset, x - offset : x + w + offset]

        # data wajah yang diambil di resize ukurannya agar konsisten
        face_selection = cv2.resize(face_offset, (100, 100))

        if skip % 10 == 0:
            # data wajah di train
            face_data.append(face_selection)
            print(f"Face {k} added to dataset.")
        k += 1

        # nampil wajah
        cv2.imshow(f"Face {k}", face_selection)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # pencet q untuk keluar loop/stop program capture
    key_pressed = cv2.waitKey(1) & 0xFF
    if key_pressed == ord('q'):
        break

# convert data wajah yang tadi terkumpul ke file nummpy
face_data = np.array(face_data)

# data wajah di kecilkan untuk penyimpanan
face_data = face_data.reshape((face_data.shape[0], -1))

# tampil jumlah data wajah yg muncul
print(f"Dataset contains {len(face_data)} faces.")

# data nya di save
np.save(dataset_path + file_name, face_data)
print(f"Dataset saved at: {dataset_path + file_name + '.npy'}")

# release camera sama close opencv window
cap.release()
cv2.destroyAllWindows()
