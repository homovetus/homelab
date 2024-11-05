#!/usr/bin/env python3

import av
import os
from uuid import UUID
import struct

path = "./build/macosx/arm64/debug/j101.mp4"
basename = os.path.splitext(path)[0]

# remove extension and add .txt at the end, so we can save it in the same folder
timestamp_path = basename + ".txt"
timestamp_RTP_interpolated_path = basename + "_RTP_interpolated.txt"
timestamp_interpolated_path = basename + "_interpolated.txt"
mata_path = basename + "_meta.txt"
print(f"timestamp out: {timestamp_path}")
print(f"timestamp_RTP_interpolated out: {timestamp_RTP_interpolated_path}")
print(f"timestamp_interpolated out: {timestamp_interpolated_path}")
print(f"meta out: {mata_path}")

container = av.open(path)
stream = container.streams.video[0]

rtp_time_infos = []
# check if meta_path exists
if os.path.exists(mata_path):
    with open(mata_path, "r") as f:
        for line in f.readlines():
            data = line.strip().split(" ")
            rtp_time_infos.append(
                (
                    float(data[0]),
                    int(data[1]),
                    int(data[2]),
                    int(data[3]),
                )
            )
else:
    for packet in container.demux(stream):
        for frame in packet.decode():
            for sd in list(frame.side_data.keys()):
                # Convert the side data to bytes
                bts = bytes(sd)

                # Extract the first 16 bytes as UUID
                uuid_bts = bts[:16]
                uuid_str = str(UUID(bytes=uuid_bts))

                # Extract the bytes for the RTPTimeInfos, see sync_recorder.h
                unix_timestamp = bts[16:24]  # 8 bytes for a double
                rtcp_ntp = bts[24:32]  # 8 bytes for unsigned 64-bit integer
                rtcp_rtp = bts[32:36]  # 4 bytes for unsigned 32-bit integer
                frame_rtp = bts[36:40]  # 4 bytes for unsigned 32-bit integer

                # Convert the byte data to a double using struct.unpack
                unix_timestamp = struct.unpack("d", unix_timestamp)[0]
                rtcp_ntp = struct.unpack("Q", rtcp_ntp)[0]
                rtcp_rtp = struct.unpack("I", rtcp_rtp)[0]
                frame_rtp = struct.unpack("I", frame_rtp)[0]
                print(f"UUID: {uuid_str}")
                print(
                    f"Unix Timestamp: {unix_timestamp}, RTCP NTP: {rtcp_ntp}, RTCP RTP: {rtcp_rtp}, Frame RTP: {frame_rtp}"
                )

                rtp_time_infos.append((unix_timestamp, rtcp_ntp, rtcp_rtp, frame_rtp))

# Save meta data to meta_path
with open(mata_path, "w") as f:
    for rtp_time_info in rtp_time_infos:
        f.write(
            f"{rtp_time_info[0]} {rtp_time_info[1]} {rtp_time_info[2]} {rtp_time_info[3]}\n"
        )


# Save unix_timestamp to timestamp_path
with open(timestamp_path, "w") as f:
    for rtp_time_info in rtp_time_infos:
        f.write(f"{rtp_time_info[0]}\n")


# Interpolate the timestamps
def ntp2unix(ntp_time):
    NTP_TIMESTAMP_DELTA = (
        2208988800  # Difference in seconds between NTP and Unix epochs: 1900 vs 1970
    )

    # Extract seconds and fractional part from NTP timestamp
    ntp_seconds = ntp_time >> 32
    ntp_fraction = ntp_time & 0xFFFFFFFF

    # Convert seconds to system time
    tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA
    # Convert fractional part to nanoseconds
    tv_nsec = int((ntp_fraction * 1e9) / (1 << 32))

    return {"tv_sec": tv_sec, "tv_nsec": tv_nsec}


def next_rtcp(index):
    current_rtcp_ntp = rtp_time_infos[index][1]
    for i in range(index + 1, len(rtp_time_infos)):
        if rtp_time_infos[i][1] != current_rtcp_ntp:
            return i
    return len(rtp_time_infos) - 1


def current_rtcp(index):
    current_rtcp_ntp = rtp_time_infos[index][1]
    for i in range(index - 1, -1, -1):
        if rtp_time_infos[i][1] != current_rtcp_ntp:
            return i + 1
    return 0


RTP_interpolated_timestamps = []
for i in range(len(rtp_time_infos)):
    current_rtp = rtp_time_infos[i][3]
    current_rtcp_index = current_rtcp(i)
    next_rtcp_index = next_rtcp(i)
    current_rtcp_ntp = rtp_time_infos[i][1]
    next_rtcp_ntp = rtp_time_infos[next_rtcp_index][1]
    current_rtcp_rtp = rtp_time_infos[current_rtcp_index][2]
    next_rtcp_rtp = rtp_time_infos[next_rtcp_index][2]

    if current_rtcp_ntp == next_rtcp_ntp:
        RTP_interpolated_timestamps.append(rtp_time_infos[i][0])
        continue
    ratio = (current_rtp - current_rtcp_rtp) / (next_rtcp_rtp - current_rtcp_rtp)

    current_unix = ntp2unix(current_rtcp_ntp)
    current_unix = current_unix["tv_sec"] + current_unix["tv_nsec"] / 1e9
    next_unix = ntp2unix(next_rtcp_ntp)
    next_unix = next_unix["tv_sec"] + next_unix["tv_nsec"] / 1e9

    # Do interpolation using only ratio and current, next timestamps
    interpolated_timestamp = current_unix + (next_unix - current_unix) * ratio

    RTP_interpolated_timestamps.append(interpolated_timestamp)

# Save the interpolated timestamps to a text file

with open(timestamp_RTP_interpolated_path, "w") as f:
    for timestamp in RTP_interpolated_timestamps:
        f.write(f"{timestamp}\n")

interpolated_timestamps = []
for i in range(len(rtp_time_infos)):
    current_rtcp_index = current_rtcp(i)
    current_rtcp_ntp = rtp_time_infos[i][1]
    next_rtcp_index = next_rtcp(i)
    next_rtcp_ntp = rtp_time_infos[next_rtcp_index][1]

    if current_rtcp_ntp == next_rtcp_ntp or current_rtcp_index == 0:
        interpolated_timestamps.append(rtp_time_infos[i][0])
        continue

    ratio = (i - current_rtcp_index) / (next_rtcp_index - current_rtcp_index)

    current_rtcp_ntp = rtp_time_infos[i][1]
    next_rtcp_ntp = rtp_time_infos[next_rtcp_index][1]
    current_unix = ntp2unix(current_rtcp_ntp)
    current_unix = current_unix["tv_sec"] + current_unix["tv_nsec"] / 1e9
    next_unix = ntp2unix(next_rtcp_ntp)
    next_unix = next_unix["tv_sec"] + next_unix["tv_nsec"] / 1e9

    # Do interpolation using only ratio and current, next timestamps
    interpolated_timestamp = current_unix + (next_unix - current_unix) * ratio
    interpolated_timestamps.append(interpolated_timestamp)

with open(timestamp_interpolated_path, "w") as f:
    for timestamp in interpolated_timestamps:
        f.write(f"{timestamp}\n")
