# RTCP-NTP-Recorder

## Overview

**RTCP-NTP-Recorder** is a tool for recording RTSP streams while embedding precise timestamps into H.264 video frames using RTCP-provided NTP information. This tool can be used for:

- Recording video and audio from RTSP streams.
- Embedding NTP timestamps from [RTCP Sender Reports](https://www4.cs.fau.de/Projects/JRTP/pmt/node83.html) into [H.264 User Data Unregistered SEI Message](https://learn.microsoft.com/en-us/openspecs/office_protocols/ms-h264pf/3d5fb9c1-efe8-4092-a60d-5321adce9c2e).
- Synchronizing cameras if they have accurate internal clocks (e.g., those synchronized with NTP servers).

## Why

When creating synchronized video footage from multiple cameras, the standard approach typically involves hardware-based synchronization methods. Examples include using [Genlock](https://en.wikipedia.org/wiki/Genlock) or custom solutions such as those provided by [Flir cameras](https://flir.custhelp.com/app/answers/detail/a_id/3385/~/flir-cameras---trigger-vs.-sync-vs.-record-start). While effective, these methods often demand specialized hardware, making them costly and less accessible.

For vision tasks that do not require extremely precise synchronization, a more cost-effective alternative is to use timestamp information from the RTCP Sender Reports provided by network cameras.

This tool offers a software-based solution for synchronizing network cameras using RTCP Sender Reports. It works with any camera supporting RTCP Sender Reports, a common feature in ONVIF-compatible cameras. With affordable options like 4K network cameras priced around $250, this approach provides a much more economical alternative to traditional hardware-based systems.

## Components

**RTCP-NTP-Recorder** consists of two main components:

1. **Recorder**:
   - A C-based client that connects to an RTSP server to record video and audio streams.
   - Embeds NTP timestamps into H.264 video frame metadata.
2. **Extractor**:
   - A Python script to extract timestamps from recorded video files.

## Installation

### Prerequisites

- **GStreamer Library**: Required for RTSP stream handling. Tested with GStreamer version 1.24.9.
  - **macOS**: Use [Homebrew](https://brew.sh/) with the command:
  ```sh
  brew install gstreamer
  ```
  - **Ubuntu 24.04**: Use `apt` with the command:
  ```sh
  sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-plugins-good gstreamer1.0-tools libgstreamer-plugins-bad1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer1.0-dev
  ```
- **Python**: Tested with version 3.12, but should work with other versions.
- **PyAV**: Python bindings for FFmpeg. Installation instructions are available on the [PyAV GitHub page](https://github.com/PyAV-Org/PyAV).
- **xmake**: Build tool used.
  - **macOS**:
  ```sh
  brew install xmake
  ```
  - **Ubuntu**:
  ```sh
  sudo apt install 7zip build-essential git xmake
  ```

### Build

Run the following command to build the **Recorder**:

```sh
xmake
```

Run the following command to generate `compile_commands.json` for supported tools (e.g., VSCode, CLion, Clangd):

```sh
xmake project -k compile_commands
```

## Usage

### Recorder

To start recording an RTSP stream, use the following command:

```sh
./recorder [options] <RTSP_URL> <output_filename_no_extension>
```

- Replace `<RTSP_URL>` with the URL of the stream.
- Replace `<output_filename_without_extension>` with the desired output filename without the extension. e.g., `LivingRoomCamera`.
- Options:
  - `-n <value>`: Maximum number of files to keep, 0 for unlimited (default: 0)
  - `-l <value>`: Maximum length of each file in seconds, 0 for unlimited (default: 300)
  - `-h`: Show help message

### Extractor

To extract timestamps from the recorded video file, use the following command:

```sh
python3 extractor.py <video_filename>
```

- Replace `<video_filename>` with the recorded video file.

When the script finishes, it will generate 4 files:

- `<video_filename>_meta.txt`: Contains the extracted metadata for each frame, it is used to avoid re-extracting the metadata.
- `<video_filename>.txt`: Contains the extracted timestamps, which is calculated by adding RTP relative time to NTP time in the most recent RTCP SR. Detailed math is described in [ntp_calc.py](./tools/ntp_calc.py)
- `<video_filename>_RTP_interpolated.txt`: Contains the timestamps interpolated using two RTCP SR packets, the ratio is based on RTP relative time, this is used to avoid time rewinding in the previous method.
- `<video_filename>_interpolated.txt`: Contains the timestamps interpolated using only RTCP SR packets and do not refer to the RTP timestamps. This method assumes frames are equally spaced in time (Not always true for some cameras). This method also ensures the timestamps are monotonically increasing.

For more information about the timestamp calculation methods, please refer to the actual [code](./extractor.py).

## Docker

A docker setup is also available for this project, which can be used to run the recorder. Extractor's docker setup is not provided as it is just a python script.

### Build Docker Image

To build the Docker image, run the following command in the project directory:

```sh
sudo docker build -t rtcp-ntp-recorder .
```

### Run Docker Container

To run the Docker container, use the following command:

```sh
docker run --rm -v <host_folder>:<mounted_folder> rtcp-ntp-recorder [options] <RTSP_URL> <mounted_folder>/<output_filename_no_extension>
```

Example:

```sh
docker run --rm -v ./storage:/storage rtcp-ntp-recorder -l 500 'rtsp://onvif:password!@192.168.0.2:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif' /storage/camera1
```

## Performance

The level of syncing has been tested with Amcrest IP cameras using different video resolutions and frame rates. Two cameras were synchronized with the same local NTP server and recorded simultaneously.

The results are as follows:

| Metric                      | RTP Timestamp | RTP Interpolated Timestamp | Interpolated Timestamp | Manual  |
| --------------------------- | ------------- | -------------------------- | ---------------------- | ------- |
| Average time diff           | -18.460       | -17.969                    | -18.499                | -31.533 |
| Standard deviation          | 48.077        | 45.329                     | 41.053                 | 33.335  |
| Absolute average time diff  | 40.458        | 38.538                     | 35.232                 | 37.135  |
| Absolute standard deviation | 31.857        | 29.866                     | 28.034                 | 26.926  |

![4K 30FPS](./test/4k-boxplot.png)

For results of other resolutions and frame rates, refer to the [test](./test) directory, the scripts for generating these plots are also available in the same directory. The test videos are not included in this repository, but can be downloaded [here](https://drive.google.com/drive/folders/1qIzWJv_rcBqx15bp4oC86xy1X5J7hAKM?usp=sharing).

In general, a sync within 3 frames can be expected for 30FPS videos.

## Caveats

### RTCP Sender Reports

The tool assumes that the camera provides RTCP Sender Reports (SR). If the stream does not provide SRs, this tool will not work. RTCP SR is required for ONVIF compatible cameras. To check if the camera sends RTCP SR, the Wireshark can be a useful tool. ![Wireshark](./test/wireshark.png)

### Frame Rate Stability

Cameras may not shoot frames at constant intervals. Here is an example of change in frame interval (1080P 10FPS), as 47:956 is expected for the clock in the second screenshot, but the actual clock is 48:059.
![Change in frame interval](./test/interval_0.png)
![Change in frame interval](./test/interval_1.png)

When testing with Amcrest IP cameras, the change in interval was reflected in the extracted timestamps, but not always. One characteristic of this Amcrest camera is that although the frame interval changes, the total number of frames is constant in each 5-minute recording. This characteristic somehow helped to show why using the interpolated method provided the lowest error and standard deviation, as the method assumes the frame rate is constant.

However, it is still recommended to test the results of using different timestamp calculation methods shown in the [extractor](#extractor) section.

### Video and Audio Encodings

The current implementation of recorder only supports H.264 video and AAC audio, which should be supported by every camera. It is possible to support encoding like H.265 using only the GStreamer library, but it is not implemented yet.

## References

The methodology of using RTCP Sender Reports to synchronize cameras is mainly based on the following research:

- de Castro, Pedro,Emanuel Moura. Multi-Camera Synchronization for Object Detection in Multiple Scenes by Computer Vision, Universidade do Porto (Portugal), Portugal, 2021. ProQuest, https://link.ezproxy.neu.edu/login?url=https://www.proquest.com/dissertations-theses/multi-camera-synchronization-object-detection/docview/3122668153/se-2.

However, the implementation was not demonstrated in the research paper, and this tool is an attempt to implement the methodology and also a supplement to solve the problem of timestamp interpolation for better synchronization.
