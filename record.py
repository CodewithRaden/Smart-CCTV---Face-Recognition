import cv2
import os
from datetime import datetime

# Create a folder for saving videos if it doesn't exist
output_folder = "recorded_videos"
os.makedirs(output_folder, exist_ok=True)

# Generate a unique file name based on date and time
current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_file_path = os.path.join(output_folder, f"video_{current_datetime}.mp4")

cap = cv2.VideoCapture(0)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Use the generated file name and path for VideoWriter
writer = cv2.VideoWriter(output_file_path, cv2.VideoWriter_fourcc(*'DIVX'), 20, (width, height))

while True:
    ret, frame = cap.read()

    writer.write(frame)

    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
writer.release()
cv2.destroyAllWindows()
