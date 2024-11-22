#!/usr/bin/env python3
import cv2
import numpy as np
import os


# Load timestamps from files
def load_timestamps(file_path):
    with open(file_path, "r") as f:
        timestamps = [float(line.strip()) for line in f.readlines()]
    return timestamps


# Find the index of the frame in the secondary video with the closest timestamp to the main video frame
def find_closest_frame(main_timestamp, secondary_timestamps):
    closest_index = np.argmin(np.abs(np.array(secondary_timestamps) - main_timestamp))
    return closest_index


# Show two frames side by side
def show_frames(frame1, frame2):
    combined_frame = np.hstack((frame1, frame2))
    cv2.imshow("Video Sync Viewer", combined_frame)


# Keyboard controls for navigation
def navigate_frames(main_video, secondary_video, main_timestamps, secondary_timestamps):
    main_frame_idx = 0  # 326

    while main_video.isOpened():
        # Set the video frame index based on the current position
        main_video.set(cv2.CAP_PROP_POS_FRAMES, main_frame_idx)

        # Read the main frame
        ret_main, main_frame = main_video.read()
        if not ret_main:
            break

        # Get the timestamp of the current main frame
        main_timestamp = main_timestamps[main_frame_idx]

        # Find the corresponding frame in the secondary video
        closest_secondary_idx = find_closest_frame(main_timestamp, secondary_timestamps)
        secondary_video.set(cv2.CAP_PROP_POS_FRAMES, closest_secondary_idx)
        ret_secondary, secondary_frame = secondary_video.read()
        if not ret_secondary:
            break

        print(f"Main Frame timestamp: {main_timestamp}")
        print(
            f"Secondary Frame timestamp at {closest_secondary_idx}: {secondary_timestamps[closest_secondary_idx]}"
        )
        # Display the frames side by side
        show_frames(main_frame, secondary_frame)

        # Wait for key press
        key = cv2.waitKey(0)

        if key == ord("q"):  # Quit
            break
        elif key == ord("f"):
            main_frame_idx = min(len(main_timestamps) - 1, main_frame_idx - 1)
            print("Previous frame", main_frame_idx)
        elif key == ord("p"):
            main_frame_idx = max(0, main_frame_idx + 1)
            print("Next frame", main_frame_idx)
        elif key == ord("s"):
            main_frame_idx = min(len(main_timestamps) - 1, main_frame_idx - 10)
            print("Backward frame", main_frame_idx)
        elif key == ord("t"):
            main_frame_idx = max(0, main_frame_idx + 10)
            print("Forward frame", main_frame_idx)
        elif key == ord("c"):
            main_frame_idx = min(len(main_timestamps) - 1, main_frame_idx - 100)
            print("Backward frame", main_frame_idx)
        elif key == ord("v"):
            main_frame_idx = max(0, main_frame_idx + 100)
            print("Forward frame", main_frame_idx)
        else:
            continue

    main_video.release()
    secondary_video.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # Load the videos
    main_video_path = "hd-low-bit-100.mp4"
    secondary_video_path = "hd-low-bit-200.mp4"

    main_video = cv2.VideoCapture(main_video_path)
    secondary_video = cv2.VideoCapture(secondary_video_path)

    # Load the timestamp files
    main_timestamps_path = os.path.splitext(main_video_path)[0] + ".txt"
    secondary_timestamps_path = os.path.splitext(secondary_video_path)[0] + ".txt"
    # main_timestamps_path = os.path.splitext(main_video_path)[0] + "_RTP_interpolated.txt"
    # secondary_timestamps_path = os.path.splitext(secondary_video_path)[0] + "_RTP_interpolated.txt"
    # main_timestamps_path = os.path.splitext(main_video_path)[0] + "_interpolated.txt"
    # secondary_timestamps_path = os.path.splitext(secondary_video_path)[0] + "_interpolated.txt"
    print(
        f"Loading timestamps from {main_timestamps_path} and {secondary_timestamps_path}"
    )

    main_timestamps = load_timestamps(main_timestamps_path)
    secondary_timestamps = load_timestamps(secondary_timestamps_path)

    # Start the frame navigation
    navigate_frames(main_video, secondary_video, main_timestamps, secondary_timestamps)
