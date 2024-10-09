#!/bin/bash

ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 timestamp.mp4
