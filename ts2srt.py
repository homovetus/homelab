import datetime


def frame_to_timecode(frame_number, fps):
    # Convert frame number to time in seconds, then format it as H:MM:SS,ms
    total_seconds = frame_number / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int((total_seconds % 1) * 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def generate_srt(input_file, output_file, fps):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        frame_number = 0
        for line in infile:
            line = line.strip()  # Remove any trailing spaces or newlines
            if line:  # Only process non-empty lines
                # read line as a number
                unixtime = float(line)
                # Convert to local time
                local_time = datetime.datetime.fromtimestamp(unixtime)

                frame_start = frame_number
                frame_end = frame_number + 1  # Each subtitle lasts for one frame

                # Convert frames to timecodes
                start_time = frame_to_timecode(frame_start, fps)
                end_time = frame_to_timecode(frame_end, fps)

                # SRT subtitle format: index, timecodes, text
                outfile.write(f"{frame_number + 1}\n")  # Subtitle index (starts at 1)
                outfile.write(f"{start_time} --> {end_time}\n")  # Timecode
                outfile.write(f"{local_time}\n\n")  # Timestamp in local time

                frame_number += 1


# Usage:
input_file = "timestamps.txt"
output_file = "timestamps.srt"
fps = 29  # Frame rate of the video (adjust as necessary)

generate_srt(input_file, output_file, fps)
