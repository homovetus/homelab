#!/bin/bash

args=(
        # General
        -y # Overwrite existing files.
        -loglevel level+verbose

        # Input
        -use_wallclock_as_timestamps 1 # This rebuilds the timestamps in the video feed.
        -avoid_negative_ts make_zero # Shift timestamps so that the first timestamp is 0.
        -fflags +genpts+discardcorrupt # Generate missing PTS if DTS is present. Discard corrupted packets.
        -rtsp_transport tcp # Use TCP for RTSP
        -i "rtsp://onvif:password!@192.168.1.4:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif"

        # Output
        -reset_timestamps 1 # Must have, otherwise recorded clips will be 10, 20, 30, 40 ... seconds long.
        -vcodec copy # No video re-encoding.
        -acodec copy # No audio re-encoding.
        -f segment # Save in segments.
        -segment_time 10 #  Increase size will require larger cache size to store multiple large files. Also, if ffmpeg loses connection to your camera at any point, the entire segment is corrupted and lost.
        -segment_atclocktime 1 # Save segments at mm:10, mm:20 ... clock time.
        -strftime 1 # String format time for file name.
        -segment_format mkv
        %Y%m%dT%H%M%S.mkv
)

# start ffmpeg to record rtsp stream
ffmpeg "${args[@]}"
