#!/bin/bash

args=(
        # General
        --eos-on-shutdown # Force EOS on sources before shutting the pipeline down

        # Pipeline
        rtspsrc
        location=rtsp://user:pass@127.0.0.1:8554/stream0
        protocols=tcp
        !
        rtph264depay
        !
        h264parse
        !
        mp4mux
        !
        filesink
        location=./camera.mp4
)

# start gstreamer to record rtsp stream
gst-launch-1.0 "${args[@]}"
