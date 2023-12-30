import cv2

# Inisialisasi objek kam
cap = cv2.VideoCapture(0)

new_width = 640
new_height = 480

# Set the video capture properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, new_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, new_height)

# Periksa apakah kamera berhasil dibuka
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# Loop utama
while True:
    # Baca frame dari kamera
    ret, frame = cap.read()

    # Periksa apakah bacaan frame berhasil
    if not ret:
        print("Error: Failed to capture frame.")
        break

    # Tampilkan frame dalam jendela
    cv2.imshow('Camera Feed', frame)

    # Tunggu tombol kunci 'q' untuk keluar dari loop
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Tutup kamera dan jendela
cap.release()
cv2.destroyAllWindows()
