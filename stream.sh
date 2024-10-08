#!/bin/bash

# Define the number of streams you want to start
NUM_STREAMS=1

# Loop over the number of streams and start an ffmpeg instance for each
for ((i=0; i<NUM_STREAMS; i++)); do
        args=(
                # General
                -loglevel level+verbose

                # Input
                -stream_loop -1 # Loop the input video indefinitely.
                -i "clock.mp4" # Input video file.

                # Output
                -c:v libx264 # Encode video with the H.264 codec.
                -f rtsp # Set the output format to RTSP.
                -rtsp_transport tcp # Use TCP as the RTSP transport protocol.
                rtsp://user:pass@localhost:8554/stream$i # RTSP output stream URL.
        )

  # Start ffmpeg for the current stream in the background
  ffmpeg "${args[@]}" &
done

# Wait for all background processes to finish
wait
