#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import os
import datetime
import statistics


def load_timestamps(file_path):
    with open(file_path, "r") as f:
        timestamps = [float(line.strip()) for line in f.readlines()]
    return timestamps


def load_ocr_timestamps(file_path):
    with open(file_path, "r") as f:
        timestamps = []
        for line in f.readlines():
            t = line.split()[-1]
            try:
                timestamps.append(datetime.datetime.strptime(t, "%H:%M:%S.%f"))
            except ValueError:
                timestamps.append(timestamps[-1])

    return timestamps


def find_closest_frame(main_timestamp, secondary_timestamps):
    # Convert secondary timestamps to a numpy array and calculate the absolute differences
    differences = np.abs(np.array(secondary_timestamps) - main_timestamp)
    # Find the index of the minimum difference
    closest_index = np.argmin(differences)
    # Find the corresponding timestamp
    closest_timestamp = secondary_timestamps[closest_index]
    # Return both the index and the closest timestamp
    return closest_timestamp, closest_index


def loop(main_timestamp, sub_timestamp, main_OCR, sub_OCR):
    ret = []
    for i in range(0, len(main_timestamp)):
        closest_timestamp, closest_index = find_closest_frame(
            main_timestamp[i], sub_timestamp
        )
        main_time_OCR = main_OCR[i]
        sub_time_OCR = sub_OCR[closest_index]

        # Calculate the difference between the OCR timestamps
        OCR_diff = (main_time_OCR - sub_time_OCR).total_seconds()
        ret.append(OCR_diff)
    return ret


main_path = "./build/macosx/arm64/debug/j101.mp4"
sub_path = "./build/macosx/arm64/debug/j201.mp4"

main_base_name = os.path.splitext(main_path)[0]
sub_base_name = os.path.splitext(sub_path)[0]

main_RTP_timestamp = load_timestamps(main_base_name + ".txt")
main_RTP_interpolated = load_timestamps(main_base_name + "_RTP_interpolated.txt")
main_interpolated = load_timestamps(main_base_name + "_interpolated.txt")
main_OCR = load_ocr_timestamps(main_base_name + "_ocr.txt")

sub_RTP_timestamp = load_timestamps(sub_base_name + ".txt")
sub_RTP_interpolated = load_timestamps(sub_base_name + "_RTP_interpolated.txt")
sub_interpolated = load_timestamps(sub_base_name + "_interpolated.txt")
sub_OCR = load_ocr_timestamps(sub_base_name + "_ocr.txt")

r_RTP = loop(main_RTP_timestamp, sub_RTP_timestamp, main_OCR, sub_OCR)
r_RTP_interpolated = loop(
    main_RTP_interpolated, sub_RTP_interpolated, main_OCR, sub_OCR
)
r_interpolated = loop(main_interpolated, sub_interpolated, main_OCR, sub_OCR)

# Find mean
print("RTP mean: ", statistics.mean(r_RTP))
print("RTP interpolated mean: ", statistics.mean(r_RTP_interpolated))
print("Interpolated mean: ", statistics.mean(r_interpolated))

# plot the data
plt.figure(figsize=(10, 6))

plt.plot(r_RTP, label="RTP")
plt.plot(r_RTP_interpolated, label="RTP interpolated")
plt.plot(r_interpolated, label="Interpolated")

plt.xlabel("Frame")
plt.ylabel("Difference in seconds")
plt.title("Difference between OCR timestamps")
plt.legend()
plt.show()
