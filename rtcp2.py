import gi

# Require the necessary GObject Introspection (gi) versions
gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
gi.require_version("GstRtp", "1.0")

from gi.repository import GObject, Gst, GstRtp, GLib

# Initialize GStreamer
Gst.init(None)

# Global variables for storing NTP and RTP times
ntp_time = 0
rtp_time = 0


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


def on_new_manager_callback(rtspsrc, manager):
    """Callback triggered when the RTSP manager is created."""
    sinkpad = manager.request_pad_simple("recv_rtcp_sink_0")
    session = manager.emit("get-internal-session", 0)
    session.connect_after("on-receiving-rtcp", on_receiving_rtcp_callback)


def on_receiving_rtcp_callback(session, buffer: Gst.Buffer):
    """Callback for processing incoming RTCP packets and extracting NTP/RTP timestamps."""
    global ntp_time, rtp_time
    rtcp_buffer = GstRtp.RTCPBuffer()

    # Map the incoming RTCP buffer for reading
    res = GstRtp.RTCPBuffer.map(buffer, Gst.MapFlags.READ, rtcp_buffer)
    rtcp_packet = GstRtp.RTCPPacket()

    # Start reading packets
    more_packets = rtcp_buffer.get_first_packet(rtcp_packet)
    while more_packets:
        # Process Sender Report (SR) RTCP packets
        if rtcp_packet.get_type() == GstRtp.RTCPType.SR:
            sender_info = rtcp_packet.sr_get_sender_info()
            ntp_time = sender_info[1]  # NTP timestamp
            rtp_time = sender_info[2]  # RTP timestamp
        # Move to the next packet
        more_packets = rtcp_packet.move_to_next()


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

    return Gst.PadProbeReturn.OK


# Define the RTSP pipeline string
pipeline_description = """
rtspsrc name=rtspsrc location=rtsp://onvif:password!@192.168.1.4:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif
! rtph264depay name=depay
! appsink name=sink
"""

# Create the GStreamer pipeline
pipeline = Gst.parse_launch(pipeline_description)

if pipeline:
    # Get the RTSP source element from the pipeline
    rtspsrc = pipeline.get_by_name("rtspsrc")

    if rtspsrc:
        # Connect the new-manager signal to the callback
        rtspsrc.connect("new-manager", on_new_manager_callback)

        # Get the depayloader and its sink pad for probing
        depay = pipeline.get_by_name("depay")
        sinkpad = depay.get_static_pad("sink")

        # Add a pad probe to monitor RTP buffers
        sinkpad.add_probe(Gst.PadProbeType.BUFFER, calculate_timestamp)

        # Start the pipeline
        pipeline.set_state(Gst.State.PLAYING)

        try:
            # Start the GLib main loop
            loop = GLib.MainLoop()
            loop.run()
        except KeyboardInterrupt:
            # Handle interruption and stop the pipeline
            pipeline.set_state(Gst.State.NULL)
    else:
        print("Error: RTSP source (rtspsrc) is null.")
else:
    print("Error: Pipeline is null.")
