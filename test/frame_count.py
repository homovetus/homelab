import os
import cv2

# find folder q1, and all file under q1


def get_frame_count(video_path):
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    return frame_count


folder = "./q2"

for root, dirs, files in os.walk(folder):
    for file in files:
        if file.endswith(".mp4"):
            video_path = os.path.join(root, file)
            frame_count = get_frame_count(video_path)
            print(f"{video_path}: {frame_count}")
