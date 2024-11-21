#!/usr/bin/env python3
import matplotlib.pyplot as plt
import os


# Load timestamps from files
def load_timestamps(file_path):
    with open(file_path, "r") as f:
        timestamps = [float(line.strip()) for line in f.readlines()]
    return timestamps


plt.figure(figsize=(10, 5))

path = "hd-100.mp4"
timestamp_path = os.path.splitext(path)[0] + ".txt"
timestamp_RTP_interpolated_path = os.path.splitext(path)[0] + "_RTP_interpolated.txt"
timestamp_interpolated_path = os.path.splitext(path)[0] + "_interpolated.txt"

timestamps = load_timestamps(timestamp_path)
timestamps_RTP_interpolated = load_timestamps(timestamp_RTP_interpolated_path)
timestamps_interpolated = load_timestamps(timestamp_interpolated_path)

x = timestamps
y = range(len(timestamps))

plt.plot(x, y, label="Original Timestamps", marker="o")
# plt.plot(
#     timestamps_RTP_interpolated, y, label="RTP Interpolated Timestamps", marker="o"
# )
# plt.plot(timestamps_interpolated, y, label="Interpolated Timestamps", marker="o")

path = "hd-200.mp4"
timestamp_path = os.path.splitext(path)[0] + ".txt"
timestamp_RTP_interpolated_path = os.path.splitext(path)[0] + "_RTP_interpolated.txt"
timestamp_interpolated_path = os.path.splitext(path)[0] + "_interpolated.txt"

timestamps = load_timestamps(timestamp_path)
timestamps_RTP_interpolated = load_timestamps(timestamp_RTP_interpolated_path)
timestamps_interpolated = load_timestamps(timestamp_interpolated_path)

x = timestamps
y = range(len(timestamps))
plt.plot(x, y, label="Original Timestamps", marker="o")
# plt.plot(
#     timestamps_RTP_interpolated, y, label="RTP Interpolated Timestamps", marker="o"
# )
# plt.plot(timestamps_interpolated, y, label="Interpolated Timestamps", marker="o")


# Label the plot
plt.legend()


plt.ylabel("Frame Index")
plt.xlabel("Timestamp (s)")
plt.title("Timestamps and Interpolated Timestamps")
plt.grid(True)
plt.show()
