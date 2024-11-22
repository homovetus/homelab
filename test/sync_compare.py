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
            t = line.split()[-2]
            confidence = line.split()[-1]
            if float(confidence) > 15:
                try:
                    timestamps.append(datetime.datetime.strptime(t, "%H:%M:%S.%f"))
                except ValueError:
                    timestamps.append(None)
            else:
                timestamps.append(None)

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
        if main_time_OCR is None or sub_time_OCR is None:
            continue
        OCR_diff = (main_time_OCR - sub_time_OCR).total_seconds() * 1000
        ret.append(OCR_diff)

    # Remove outliers
    ret = [i for i in ret if i < 200 and i > -200]
    return ret


def once_loop(main_OCR, sub_OCR, main_start, sub_start):
    ret = []
    diff = sub_start - main_start
    for i in range(main_start, min(len(main_OCR), len(sub_OCR))):
        if i + diff >= len(sub_OCR):
            break
        main_time_OCR = main_OCR[i]
        sub_time_OCR = sub_OCR[i + diff]

        # Calculate the difference between the OCR timestamps
        if main_time_OCR is None or sub_time_OCR is None:
            continue
        OCR_diff = (main_time_OCR - sub_time_OCR).total_seconds() * 1000
        ret.append(OCR_diff)
    ret = [i for i in ret if i < 200 and i > -200]
    return ret


def test(
    main_video_path, sub_video_path, title, manual_main_start=0, manual_sub_start=0
):
    main_base_name = os.path.splitext(main_video_path)[0]
    sub_base_name = os.path.splitext(sub_video_path)[0]
    plot_name = main_base_name[0:-4] + "-boxplot.png"

    main_RTP_timestamp = load_timestamps(main_base_name + ".txt")
    main_RTP_interpolated = load_timestamps(main_base_name + "_RTP_interpolated.txt")
    main_interpolated = load_timestamps(main_base_name + "_interpolated.txt")
    main_OCR = load_ocr_timestamps(main_base_name + "_ocr.txt")
    sub_RTP_timestamp = load_timestamps(sub_base_name + ".txt")
    sub_RTP_interpolated = load_timestamps(sub_base_name + "_RTP_interpolated.txt")
    sub_interpolated = load_timestamps(sub_base_name + "_interpolated.txt")
    sub_OCR = load_ocr_timestamps(sub_base_name + "_ocr.txt")

    RTP_diffs = loop(main_RTP_timestamp, sub_RTP_timestamp, main_OCR, sub_OCR)
    RTP_interpolated_diffs = loop(
        main_RTP_interpolated, sub_RTP_interpolated, main_OCR, sub_OCR
    )
    interpolated_diffs = loop(main_interpolated, sub_interpolated, main_OCR, sub_OCR)
    once_diffs = once_loop(main_OCR, sub_OCR, manual_main_start, manual_sub_start)

    # print with 3 decimal points
    print(
        "Average time diff using RTP timestamp",
        "{:.3f}".format(statistics.mean(RTP_diffs)),
    )
    print(
        "Average time diff using RTP interpolated timestamp",
        "{:.3f}".format(statistics.mean(RTP_interpolated_diffs)),
    )
    print(
        "Average time diff using interpolated timestamp",
        "{:.3f}".format(statistics.mean(interpolated_diffs)),
    )
    print(
        "Average time diff using once loop",
        "{:.3f}".format(statistics.mean(once_diffs)),
    )

    print("RTP standard deviation: ", "{:.3f}".format(statistics.stdev(RTP_diffs)))
    print(
        "RTP interpolated standard deviation: ",
        "{:.3f}".format(statistics.stdev(RTP_interpolated_diffs)),
    )
    print(
        "Interpolated standard deviation: ",
        "{:.3f}".format(statistics.stdev(interpolated_diffs)),
    )
    print(
        "Once loop standard deviation: ", "{:.3f}".format(statistics.stdev(once_diffs))
    )
    print()

    plt.figure(figsize=(10, 6))
    data = [RTP_diffs, RTP_interpolated_diffs, interpolated_diffs, once_diffs]
    plt.boxplot(
        data,
        tick_labels=["RTP", "RTP Interpolated", "Interpolated", "Manual"],
        showmeans=True,
    )
    plt.xlabel("Timestamp Types")
    plt.ylabel("Difference in milliseconds")
    plt.title(f"Time diff between cameras, using OCR timestamps ({title})")
    plt.savefig(plot_name)

    # Plot once_diffs, x and y axis
    plt.figure(figsize=(10, 6))
    plt.plot(once_diffs)
    plt.xlabel("Frame")
    plt.ylabel("Difference in milliseconds")
    plt.title(f"Time diff between cameras, using OCR timestamps ({title})")
    plt.show()

    # Find mean for absolute differences
    RTP_diffs = [abs(i) for i in RTP_diffs]
    RTP_interpolated_diffs = [abs(i) for i in RTP_interpolated_diffs]
    interpolated_diffs = [abs(i) for i in interpolated_diffs]
    once_diffs = [abs(i) for i in once_diffs]
    print(
        "Average absolute time diff using RTP timestamp",
        "{:.3f}".format(statistics.mean(RTP_diffs)),
    )
    print(
        "Average absolute time diff using RTP interpolated timestamp",
        "{:.3f}".format(statistics.mean(RTP_interpolated_diffs)),
    )
    print(
        "Average absolute time diff using interpolated timestamp",
        "{:.3f}".format(statistics.mean(interpolated_diffs)),
    )
    print(
        "Average absolute time diff using once loop",
        "{:.3f}".format(statistics.mean(once_diffs)),
    )
    print("RTP standard deviation: ", "{:.3f}".format(statistics.stdev(RTP_diffs)))
    print(
        "RTP interpolated standard deviation: ",
        "{:.3f}".format(statistics.stdev(RTP_interpolated_diffs)),
    )
    print(
        "Interpolated standard deviation: ",
        "{:.3f}".format(statistics.stdev(interpolated_diffs)),
    )
    print(
        "Once loop standard deviation: ", "{:.3f}".format(statistics.stdev(once_diffs))
    )
    print()


test("4k-100.mp4", "4k-200.mp4", "4K 30Hz", 9, 7)
test("4k-10hz-100.mp4", "4k-10hz-200.mp4", "4K 10Hz", 0, 0)
test("hd-100.mp4", "hd-200.mp4", "HD 30Hz", 8, 9)
test("hd-low-bit-100.mp4", "hd-low-bit-200.mp4", "HD Low Bitrate 30Hz", 21, 20)
