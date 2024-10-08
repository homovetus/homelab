import gi
import logging

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
gi.require_version("GstRtp", "1.0")
from gi.repository import Gst, GLib, GstRtp

logging.basicConfig(
    level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize GStreamer
Gst.init(None)

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

# Create the pipeline
pipeline = Gst.Pipeline.new("pipeline")

# Create the elements manually
rtspsrc = Gst.ElementFactory.make("rtspsrc", "rtspsrc")
rtph265depay = Gst.ElementFactory.make("rtph264depay", "depay")
appsink = Gst.ElementFactory.make("appsink", "sink")

# Check that all elements are created successfully
if not pipeline or not rtspsrc or not rtph265depay or not appsink:
    print("Failed to create some elements.")
    exit(-1)

# Set the RTSP source properties
rtspsrc.set_property(
    "location",
    # "rtsp://user:pass@127.0.0.1:8554/stream0",
    "rtsp://onvif:password!@192.168.1.4:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif",
)

# Disable automatic buffering in appsink (use pull mode)
appsink.set_property("emit-signals", True)
appsink.set_property("sync", False)

# Add elements to the pipeline
pipeline.add(rtspsrc)
pipeline.add(rtph265depay)
pipeline.add(appsink)

# Link elements manually where possible
# rtspsrc dynamically generates pads, so we need to handle that separately
rtph265depay.link(appsink)


# Function to link rtspsrc's dynamic pad to the rtph264depay
def on_pad_added(src, pad):
    print("Dynamic pad created, linking depayloader...")
    depay_sink_pad = rtph265depay.get_static_pad("sink")
    if depay_sink_pad.is_linked():
        print("Sink pad already linked. Ignoring.")
        return
    pad.link(depay_sink_pad)


# Connect signal to the pad-added event of rtspsrc
rtspsrc.connect("pad-added", on_pad_added)


# Function to handle new samples from the appsink
def on_new_sample(sink):
    sample = sink.emit("pull-sample")
    if sample:
        buf = sample.get_buffer()
        # Extract data from buffer and process it
        # print("Received new sample with size:", buf.get_size())
        return Gst.FlowReturn.OK
    return Gst.FlowReturn.ERROR


# Connect the appsink's new-sample signal to the callback
appsink.connect("new-sample", on_new_sample)


# Function to handle RTCP packets and extract NTP/RTP timestamps
def on_receiving_rtcp_callback(session, buffer: Gst.Buffer):
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
            time_converter.convert_ntp_to_datetime(ntp_time)
            print(time_converter.tv_sec)
            rtp_time = sender_info[2]  # RTP timestamp
        #     print(rtp_time)
        # Move to the next packet
        more_packets = rtcp_packet.move_to_next()


# Function to handle new RTSP manager for RTCP
def on_new_manager_callback(rtspsrc, manager):
    """Callback triggered when the RTSP manager is created."""
    print("new manager callback")
    rtcp_pad = manager.request_pad_simple("recv_rtcp_sink_0")
    if not rtcp_pad:
        print("Failed to request RTCP pad.")
        return
    session = manager.emit("get-internal-session", 0)
    print("session created")
    if not session:
        print("Failed to get internal session.")
        return
    session.connect_after("on-receiving-rtcp", on_receiving_rtcp_callback)


# Connect the rtspsrc manager signal to handle RTCP packets
rtspsrc.connect("new-manager", on_new_manager_callback)

# Start playing the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Run the GLib main loop to keep the pipeline active
loop = GLib.MainLoop()

try:
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    # Release the RTCP pad if it was created
    #     if rtcp_pad:
    #         manager = rtspsrc.get_internal_element()
    #         if manager:
    #             manager.release_request_pad(rtcp_pad)
    # Stop the pipeline when done
    pipeline.set_state(Gst.State.NULL)
