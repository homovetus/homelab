import datetime
import matplotlib.pyplot as plt
import os


def load_ocr_timestamps(file_path):
    with open(file_path, "r") as f:
        timestamps = []
        for line in f.readlines():
            t = line.split()[-2]
            confidence = line.split()[-1]
            if float(confidence) > 15:
                try:
                    timestamps.append(datetime.datetime.strptime(t, "%H:%M:%S.%f"))
                except ValueError:
                    timestamps.append(None)
            else:
                print("Low confidence: ", t)
                timestamps.append(None)

    return timestamps


file_name = "hd-low-bit-100.mp4"
file_base_name = os.path.splitext(file_name)[0]
plot_name = file_base_name[0:-4] + "-consec_ocr_diff.png"

timestamps = load_ocr_timestamps(file_base_name + "_ocr.txt")
print(len(timestamps))

x = []
diffs = []
for i in range(1, len(timestamps) - 1):
    if timestamps[i] is not None and timestamps[i + 1] is not None:
        diff = (timestamps[i + 1] - timestamps[i]).total_seconds() * 1000
        if diff < 1000 and diff > 0:
            diffs.append(diff)
            x.append(i)

# plot the differences using x and diffs
plt.plot(x, diffs)
plt.xlabel("Frame number")
plt.ylabel("Difference in ms")
plt.title("Difference between consecutive OCR timestamps (HD 30Hz Low Bitrate)")
plt.savefig(plot_name)
plt.show()
