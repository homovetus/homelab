#!/usr/bin/env python
from datetime import datetime
import cv2
import pytesseract


def extract_timestamp(frame, x, y, w, h):
    CONFIG = r"--psm 6 -c tessedit_char_whitelist=0123456789:"
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    roi = thresh[y : y + h, x : x + w]

    data = pytesseract.image_to_data(
        roi, config=CONFIG, output_type=pytesseract.Output.DICT
    )

    # Extract text and confidence for each word detected
    text = ""
    confidence = 0
    if data["text"]:
        # Join all recognized text into one string and average confidence
        text = "".join(data["text"]).strip()
        confidence_values = [
            int(data["conf"][i])
            for i in range(len(data["conf"]))
            if data["conf"][i] != "-1"
        ]
        confidence = (
            sum(confidence_values) / len(confidence_values) if confidence_values else 0
        )

    # Keep only digits and colons
    text = text[:12] if len(text) > 12 else text

    # Show the image (optional)
    cv2.imshow("ROI", roi)
    cv2.waitKey(1)

    # Parse the timestamp text to a datetime object
    try:
        timestamp = datetime.strptime(text, "%H:%M:%S:%f")
        return timestamp, confidence
    except ValueError:
        print(f"Invalid timestamp: {text}, Confidence: {confidence:.2f}")
        return None, confidence


def ocr(video, x, y, w, h, start_frame_idx=0):
    ocr_out = video.replace(".mp4", "_ocr.txt")

    video = cv2.VideoCapture(video)
    with open(ocr_out, "a") as ocr_out_file:
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        for i in range(start_frame_idx, total_frames):
            # Set the video frame index based on the current position
            video.set(cv2.CAP_PROP_POS_FRAMES, i)

            # Read the main frame
            ret, frame = video.read()
            if not ret:
                break

            # Extract the timestamp and confidence from the main frame
            ocr_timestamp, confidence = extract_timestamp(frame, x, y, w, h)

            # Print the timestamps and confidence
            print(f"Frame {i}: {ocr_timestamp}, Confidence: {confidence:.2f}")

            # Write the frame index, timestamp, and confidence to the file
            ocr_out_file.write(f"{i} {ocr_timestamp} {confidence:.2f}\n")

    video.release()


video_path = "4k-10hz-100.mp4"
ocr(video_path, x=1280, y=440, w=1060, h=140)
video_path = "4k-10hz-200.mp4"
ocr(video_path, x=1280, y=440, w=1060, h=140)
video_path = "4k-100.mp4"
ocr(video_path, x=1280, y=440, w=1060, h=140)
video_path = "4k-200.mp4"
ocr(video_path, x=1280, y=440, w=1060, h=140)
