from datetime import datetime
import cv2
import pytesseract


def extract_timestamp(frame, x, y, w, h):
    CONFIG = r"--psm 6 -c tessedit_char_whitelist=0123456789:"
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    roi = thresh[y : y + h, x : x + w]

    text = pytesseract.image_to_string(roi, config=CONFIG)
    # keep only digits and colons
    text = text.strip()
    # only keep 12 characters, e.g. 00:00:00.000
    text = text[:12]

    # show the image
    cv2.imshow("ROI", roi)
    cv2.waitKey(1)

    # parse the timestamp text to a datetime object
    try:
        timestamp = datetime.strptime(text, "%H:%M:%S:%f")
        return timestamp
    except ValueError:
        print(f"Invalid timestamp: {text}")
        return None


def ocr(video, x, y, w, h, start_frame_idx=0):
    frame_idx = start_frame_idx
    ocr_out = video.replace(".mp4", "_ocr.txt")

    video = cv2.VideoCapture(video)
    with open(ocr_out, "a") as ocr_out:
        while video.isOpened():
            # Set the video frame index based on the current position
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

            # Read the main frame
            ret, frame = video.read()
            if not ret:
                break

            # Extract the timestamp from the main frame
            ocr_timestamp = extract_timestamp(frame, x, y, w, h)

            # Print the timestamps
            print("Frame timestamp:", ocr_timestamp)

            # write the frame index, main frame timestamp, secondary frame timestamp, time delta
            ocr_out.write(f"{frame_idx} {ocr_timestamp}\n")

            frame_idx += 1

    video.release()


main_video_path = "./build/macosx/arm64/debug/m101.mp4"
secondary_video_path = "./build/macosx/arm64/debug/m201.mp4"

ocr(main_video_path, 1420, 700, 730, 170, 6067)
ocr(secondary_video_path, 1850, 900, 800, 150, 0)
