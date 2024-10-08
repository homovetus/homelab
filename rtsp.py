import gi
import logging
import sys

gi.require_version("GLib", "2.0")
gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")

from gi.repository import Gst, GLib

logging.basicConfig(
    level=logging.DEBUG, format="[%(name)s] [%(levelname)8s] - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize GStreamer
Gst.init(sys.argv[1:])

# Create the pipeline
pipeline = Gst.Pipeline.new("rtsp-pipeline")

# Create the elements manually
rtspsrc = Gst.ElementFactory.make("rtspsrc", "src")
rtph264depay = Gst.ElementFactory.make("rtph264depay", "depay")
appsink = Gst.ElementFactory.make("appsink", "sink")

# Check that all elements are created successfully
if not pipeline or not rtspsrc or not rtph264depay or not appsink:
    print("Failed to create some elements.")
    exit(-1)

# Set the RTSP source properties
rtspsrc.set_property(
    "location",
    "rtsp://user:pass@127.0.0.1:8554/stream0",
)

# Disable automatic buffering in appsink (use pull mode)
appsink.set_property("emit-signals", True)
appsink.set_property("sync", False)

# Add elements to the pipeline
pipeline.add(rtspsrc)
pipeline.add(rtph264depay)
pipeline.add(appsink)

# Link elements manually where possible
# rtspsrc dynamically generates pads, so we need to handle that separately
rtph264depay.link(appsink)


# Function to link rtspsrc's dynamic pad to the rtph264depay
def on_pad_added(src, pad):
    print("Dynamic pad created, linking depayloader...")
    depay_sink_pad = rtph264depay.get_static_pad("sink")
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
        print("Received new sample with size:", buf.get_size())
        return Gst.FlowReturn.OK
    return Gst.FlowReturn.ERROR


# Connect the appsink's new-sample signal to the callback
appsink.connect("new-sample", on_new_sample)

# Start playing the pipeline
pipeline.set_state(Gst.State.PLAYING)

# Run the GLib main loop to keep the pipeline active
loop = GLib.MainLoop()

try:
    loop.run()
except KeyboardInterrupt:
    pass
finally:
    # Stop the pipeline when done
    pipeline.set_state(Gst.State.NULL)
