import cv2
import datetime


def read_text_file(file_path):
    with open(file_path, "r") as f:
        return f.readlines()


def display_frame_with_text(video_path, text_path):
    # Read the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Read the text file
    lines = read_text_file(text_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Total frames in video: {total_frames}")
    num_lines = len(lines)

    if num_lines != total_frames:
        print(
            f"Warning: The number of lines in text file ({num_lines}) doesn't match the number of frames ({total_frames}) in the video."
        )

    current_frame = 3000

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = cap.read()

        if not ret:
            print("Error: Failed to retrieve the frame.")
            break

        # Add corresponding text from file (if exists) to the frame
        if current_frame < num_lines:
            text = lines[current_frame].strip()
            unixtime = float(text)
            # Convert to local time
            text = datetime.datetime.fromtimestamp(unixtime)
            # Convert to string with milliseconds
            text = text.strftime("%Y-%m-%d %H:%M:%S.%f")
            frame_height, frame_width = frame.shape[:2]
            # Calculate the position for upper-right placement
            text_x = frame_width - 500  # 10 px padding from right
            text_y = 50  # 10 px padding from top

            cv2.putText(
                frame,
                text,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        # Display the frame
        cv2.imshow("Video Frame", frame)

        key = cv2.waitKey(0) & 0xFF
        if key == ord("f"):
            if current_frame < total_frames - 10:
                current_frame += 10
        elif key == ord("b"):
            if current_frame > 10:
                current_frame -= 10
        elif key == ord("n"):  # Next frame
            if current_frame < total_frames - 1:
                current_frame += 1
        elif key == ord("p"):  # Previous frame
            if current_frame > 0:
                current_frame -= 1
        elif key == 27:  # Esc key to exit
            break

    # Release the video and close the window
    cap.release()
    cv2.destroyAllWindows()


# Replace with your video and text file paths
video_file = "timestamp.mp4"
text_file = "timestamps.txt"

display_frame_with_text(video_file, text_file)
