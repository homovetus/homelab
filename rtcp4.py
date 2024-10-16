#!/usr/bin/env python3
import gi
import sys

gi.require_version("Gst", "1.0")
gi.require_version("GstRtp", "1.0")
gi.require_version("GstVideo", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gst, GstRtp, GstVideo, GLib

# initialize GStreamer
Gst.init(sys.argv[1:])

rtcp_ntp = 0
rtcp_rtp = 0
ntp_timestamps = []


class UnixTime:
    """Helper class to handle time conversion between NTP and datetime."""

    def __init__(self):
        self.sec = 0  # Store seconds
        self.usec = 0  # Store microseconds

    def convert_ntp_to_datetime(self, ntp_timestamp):
        """Convert NTP timestamp to system time (seconds and microseconds)."""
        if ntp_timestamp > 0:
            ntp_seconds, ntp_fraction = divmod(ntp_timestamp, 2**32)
            self.sec = ntp_seconds - 2208988800  # Convert NTP to Unix epoch
            self.usec = (ntp_fraction * 1000000) // 2**32  # Convert fractional part


# Create a single instance of UnixTime
unix_time = UnixTime()


def on_receiving_rtcp_callback(session, buffer: Gst.Buffer):
    global rtcp_ntp, rtcp_rtp
    rtcp_buffer = GstRtp.RTCPBuffer()

    # Map the incoming RTCP buffer for reading
    GstRtp.RTCPBuffer.map(buffer, Gst.MapFlags.READ, rtcp_buffer)
    rtcp_packet = GstRtp.RTCPPacket()

    # Start reading packets
    next_packet = rtcp_buffer.get_first_packet(rtcp_packet)
    while next_packet:
        # Process Sender Report (SR) RTCP packets
        if rtcp_packet.get_type() == GstRtp.RTCPType.SR:
            sender_info = rtcp_packet.sr_get_sender_info()
            rtcp_ntp = sender_info[1]  # NTP timestamp
            rtcp_rtp = sender_info[2]  # RTP timestamp
        # Move to the next packet
        next_packet = rtcp_packet.move_to_next()


def on_new_manager_callback(rtspsrc, manager):
    """Callback triggered when the RTSP manager is created."""
    rtcp_pad = manager.request_pad_simple("recv_rtcp_sink_0")
    if not rtcp_pad:
        print("Failed to request RTCP pad.")
        return
    session = manager.emit("get-internal-session", 0)
    if not session:
        print("Failed to get internal session.")
        return
    session.connect_after("on-receiving-rtcp", on_receiving_rtcp_callback)


def calculate_frame_timestamp(pad, info):
    """Callback for calculating timestamp from the RTP header and NTP timestamp."""

    # Map the incoming RTP buffer for reading
    buffer = info.get_buffer()

    # res, info = buffer.map(Gst.MapFlags.WRITE)
    referenceTimestampMeta = buffer.get_reference_timestamp_meta()
    if referenceTimestampMeta:
        print(referenceTimestampMeta.timestamp)

    res, rtp_buffer = GstRtp.RTPBuffer.map(buffer, Gst.MapFlags.READ)
    # Check if the marker bit is set (indicating end of a frame)
    marker_bit = rtp_buffer.get_marker()
    if marker_bit:
        # Calculate the RTP timestamp difference (assuming 90kHz clock)
        rtp_diff = float(rtp_buffer.get_timestamp() - rtcp_rtp) / 90000.0

        # Convert the NTP time to system time (seconds and microseconds)
        unix_time.convert_ntp_to_datetime(rtcp_ntp)

        # Calculate the final timestamp
        timestamp = float(unix_time.sec) + float(unix_time.usec) / 1000000.0 + rtp_diff
        print(
            f"Timestamp: {timestamp}, NTP in SR: {rtcp_ntp}, "
            f"RTP in SR: {rtcp_rtp}, RTP header timestamp: {rtp_buffer.get_timestamp()}, "
            f"Marker bit: {marker_bit}"
        )
        ntp_timestamps.append(timestamp)

    return Gst.PadProbeReturn.OK


def inject_sei(pad, info):
    buffer = info.get_buffer()
    res, info = buffer.map(Gst.MapFlags.WRITE)
    GstVideo.buffer_add_video_sei_user_data_unregistered_meta(
        buffer, 114, 51, sys.getsizeof(114514)
    )

    return Gst.PadProbeReturn.OK


# Create the GStreamer pipeline
pipeline = Gst.parse_launch(
    " rtspsrc name=rtspsrc protocols=tcp location=rtsp://user:pass@127.0.0.1:8554/stream0 ! "
    " rtpjitterbuffer name=rtpjitterbuffer ! "
    " rtph264depay name=rtph264depay ! "
    " h264parse name=h264parse ! "
    " splitmuxsink name=splitter location=video%02d.mp4 max-size-time=10000000000 max-size-bytes=1000000"
)

loop = GLib.MainLoop.new(None, False)
bus = pipeline.get_bus()

rtspsrc = pipeline.get_by_name("rtspsrc")
rtspsrc.connect("new-manager", on_new_manager_callback)
rtspsrc.set_property("add-reference-timestamp-meta", True)

rtpjitterbuffer = pipeline.get_by_name("rtpjitterbuffer")
# rtpjitterbuffer.set_property("add-reference-timestamp-meta", True)

depay = pipeline.get_by_name("rtph264depay")
depaysink = depay.get_static_pad("sink")
depaysink.add_probe(Gst.PadProbeType.BUFFER, calculate_frame_timestamp)

h264parse = pipeline.get_by_name("h264parse")
parsesrc = h264parse.get_static_pad("src")
# parsesrc.add_probe(Gst.PadProbeType.BUFFER, inject_sei)

# start recording
try:
    print("Running...")
    pipeline.set_state(Gst.State.PLAYING)
    loop.run()
except KeyboardInterrupt:
    print("Stopping the pipeline...")
    pipeline.send_event(Gst.Event.new_eos())
    # Wait for gstreamer to fully stop, otherwise file will be corrupted
    print("Waiting for the EOS message on the bus")
    # This method will block until the EOS message is received
    bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
finally:
    # Stop the pipeline when done
    print("Stopping pipeline")
    pipeline.set_state(Gst.State.NULL)
    # save the timestamps to a file
    print(f"Gathered {len(ntp_timestamps)} timestamps")
    print("last timestamp", ntp_timestamps[-1])
    time_file = open("timestamps.txt", "w")
    for ts in ntp_timestamps:
        time_file.write(f"{ts}\n")
    time_file.flush()  # Ensure that data is written
    time_file.close()  # Close the file properly
