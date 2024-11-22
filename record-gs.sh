#!/bin/bash
input_url='rtsp://onvif:password!@192.168.0.136:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif'
args=(
    # General
    --eos-on-shutdown # Force EOS on sources before shutting the pipeline down

    # Pipeline
    rtspsrc location=$input_url protocols=tcp name=rtspsrc
    rtspsrc. ! rtph264depay ! h264parse ! queue ! mux. # Video stream
    rtspsrc. ! rtpmp4gdepay ! aacparse ! queue ! mux.audio_0 # Audio stream

    # Muxing and output
    splitmuxsink name=mux location=%s%%02d.mp4 max-size-time=300000000000 max-size-bytes=500000000
)

# Start GStreamer to record RTSP stream
gst-launch-1.0 "${args[@]}"
