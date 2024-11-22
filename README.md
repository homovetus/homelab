# RTCP-NTP-Recorder

## Overview

**RTCP-NTP-Recorder** is a tool for recording RTSP streams while embedding precise timestamps into H.264 video frames using RTCP-provided NTP information. This tool is useful for:

- Recording RTSP streams.
- Embedding NTP timestamps from RTCP Sender Reports into H.264 video frames.
- Synchronizing cameras connected to the same NTP server.

## Components

**RTCP-NTP-Recorder** is composed of two key components:

1. **Recorder**:
   - A C-based client that connects to an RTSP server to record video and audio streams.
   - Embeds NTP timestamps into H.264 frames.
2. **Extractor**:
   - A Python script to extract timestamps from recorded video files.

## Prerequisites

### Recorder

- **GStreamer Library**: Required for RTSP stream handling. Tested with GStreamer version 1.24.9.
- **xmake Build System**: Used to compile the C-based recorder.

### Extractor

- **Python 3.12**: The script has been tested with this version.
- **PyAV Library**: Python bindings for FFmpeg. Installation instructions are available on the [PyAV GitHub page](https://github.com/PyAV-Org/PyAV).

## Installation

### GStreamer Installation

Install GStreamer using the package manager of your system:

- **macOS**: Use [Homebrew](https://brew.sh/) with the command:
  ```sh
  brew install gstreamer
  ```
- **Ubuntu**: Use `apt` with the command:
  ```sh
  sudo apt install libgstreamer1.0-dev
  ```

### Build

run the following command to build the **Recorder**:

```sh
xmake
```

## Usage

To start recording an RTSP stream, use the following command:

```sh
./recorder <RTSP_URL> <output_filename_without_extension>
```

- Replace `<RTSP_URL>` with the RTSP URL of the stream.
- Replace `<output_filename_without_extension>` with the desired output filename without the extension. e.g. `LivingRoomCamera`.

To extract timestamps from the recorded video file, use the following command:

```sh
python3 extractor.py <video_filename>
```

- Replace `<video_filename>` with the recorded video file.
