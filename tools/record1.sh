#!/bin/sh

# Input argument to specify file name
input_arg="$1"

# Determine output by appending 1 to the input argument
output_arg="${input_arg}1"

# Input URL
input_url='rtsp://onvif:password!@192.168.0.136:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif'

# Run command
cd ../bin
./recorder "$input_url" "$output_arg"
