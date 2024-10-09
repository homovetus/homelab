#!/usr/bin/env python3
import gi
import sys

gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstRtp", "1.0")

from gi.repository import Gst, GstRtp, GLib

ntp_time = 0
rtp_time = 0

timestamps = []
time_file = open("timestamps.txt", "w")


class TimeValue:
    """Helper class to handle time conversion between NTP and datetime."""

    def __init__(self):
        self.tv_sec = 0  # Store seconds
        self.tv_usec = 0  # Store microseconds

    def convert_ntp_to_datetime(self, ntp_timestamp):
        """Convert NTP timestamp to system time (seconds and microseconds)."""
        if ntp_timestamp > 0:
            ntp_seconds, ntp_fraction = divmod(ntp_timestamp, 2**32)
            self.tv_sec = ntp_seconds - 2208988800  # Convert NTP to Unix epoch
            self.tv_usec = (ntp_fraction * 1000000) // 2**32  # Convert fractional part


# Create a single instance of TimeValue
time_converter = TimeValue()

# initialize GStreamer
Gst.init(sys.argv[1:])

# Create the GStreamer pipeline
pipeline = Gst.parse_launch(
    # " rtspsrc name=camerartsp location=rtsp://user:pass@127.0.0.1:8554/stream0 protocols=tcp ! "
    " rtspsrc name=camerartsp protocols=tcp location=rtsp://onvif:password!@192.168.0.13:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif ! "
    " rtph264depay name=rtpdepay ! "
    " h264parse ! "
    " matroskamux ! "
    " filesink location=./timestamp.mkv"
)

bus = pipeline.get_bus()


def on_message(bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop):
    t = message.type
    if t == Gst.MessageType.EOS:
        print("End-of-stream")
        loop.quit()
    elif t == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print(f"Error: {err}, {debug}")
        loop.quit()
    return True


loop = GLib.MainLoop.new(None, False)
bus.add_watch(GLib.PRIORITY_DEFAULT, on_message, loop)


def on_receiving_rtcp_callback(session, buffer: Gst.Buffer):
    global ntp_time, rtp_time
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
            ntp_time = sender_info[1]  # NTP timestamp
            rtp_time = sender_info[2]  # RTP timestamp
            print(ntp_time)
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


def calculate_timestamp(pad, info):
    """Callback for calculating timestamp from the RTP header and NTP timestamp."""
    global ntp_time, rtp_time

    # Map the incoming RTP buffer for reading
    res, rtp_buffer = GstRtp.RTPBuffer.map(info.get_buffer(), Gst.MapFlags.READ)

    # Convert the NTP time to system time (seconds and microseconds)
    time_converter.convert_ntp_to_datetime(ntp_time)

    # Calculate the RTP timestamp difference (assuming 90kHz clock)
    rtp_diff = float(rtp_buffer.get_timestamp() - rtp_time) / 90000.0

    # Calculate the final timestamp
    timestamp = (
        float(time_converter.tv_sec)
        + float(time_converter.tv_usec) / 1000000.0
        + rtp_diff
    )

    # Check if the marker bit is set (indicating end of a frame)
    marker_bit = rtp_buffer.get_marker()
    if marker_bit:
        print(
            f"Timestamp: {timestamp}, NTP in SR: {ntp_time}, "
            f"RTP in SR: {rtp_time}, RTP header timestamp: {rtp_buffer.get_timestamp()}, "
            f"Marker bit: {marker_bit}"
        )
        timestamps.append(timestamp)

    return Gst.PadProbeReturn.OK


rtspsrc = pipeline.get_by_name("camerartsp")
rtspsrc.connect("new-manager", on_new_manager_callback)

depay = pipeline.get_by_name("rtpdepay")
sinkpad = depay.get_static_pad("sink")
sinkpad.add_probe(Gst.PadProbeType.BUFFER, calculate_timestamp)

# start recording
try:
    print("Running...")
    pipeline.set_state(Gst.State.PLAYING)
    loop.run()
except KeyboardInterrupt:
    print("Stopping the pipeline...")
    pipeline.send_event(Gst.Event.new_eos())
    print("Waiting for the EOS message on the bus")
    bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
finally:
    # Release the RTCP pad if it was created
    #     if rtcp_pad:
    #         manager = rtspsrc.get_internal_element()
    #         if manager:
    #             manager.release_request_pad(rtcp_pad)
    # Stop the pipeline when done
    print("Stopping pipeline")
    pipeline.set_state(Gst.State.NULL)
    # save the timestamps to a file
    print(f"Gathered {len(timestamps)} timestamps")
    print("last timestamp", timestamps[-1])
    for ts in timestamps:
        time_file.write(f"{ts}\n")
    time_file.flush()  # Ensure that data is written
    time_file.close()  # Close the file properly
