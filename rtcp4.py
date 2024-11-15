#!/usr/bin/env python3
import gi
import sys

gi.require_version("Gst", "1.0")
gi.require_version("GstRtp", "1.0")
gi.require_version("GstVideo", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gst, GstRtp, GLib

# initialize GStreamer
Gst.init(sys.argv[1:])


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


class RTSPPipeline:
    def __init__(self):
        self.rtcp_ntp = 0
        self.rtcp_rtp = 0
        self.timestamp_index = 0
        self.ntp_timestamps = []
        self.unix_time = UnixTime()

        self.loop = GLib.MainLoop.new(None, False)
        self.pipeline = Gst.parse_launch(
            # " rtspsrc name=rtspsrc protocols=tcp location=rtsp://user:pass@127.0.0.1:8554/stream0 ! "
            " rtspsrc name=rtspsrc protocols=tcp location=rtsp://onvif:password!@192.168.0.13:554/cam/realmonitor?channel=1&subtype=0&unicast=true&proto=Onvif ! "
            " rtpjitterbuffer ! "
            " rtph264depay name=rtph264depay ! "
            " h264parse name=h264parse ! "
            " splitmuxsink name=splitter location=video%02d.mp4 max-size-time=300000000000 max-size-bytes=0"
        )
        self.bus = self.pipeline.get_bus()

        self.rtspsrc = self.pipeline.get_by_name("rtspsrc")
        self.rtph264depay = self.pipeline.get_by_name("rtph264depay")
        self.h264parse = self.pipeline.get_by_name("h264parse")

        self.rtspsrc.set_property("add-reference-timestamp-meta", True)
        self.rtspsrc.connect("new-manager", self.on_new_manager_callback)

        depaysink = self.rtph264depay.get_static_pad("sink")
        depaysink.add_probe(Gst.PadProbeType.BUFFER, self.calculate_frame_timestamp)

    def start_pipeline(self):
        try:
            print("Running...")
            self.pipeline.set_state(Gst.State.PLAYING)
            self.loop.run()
        except KeyboardInterrupt:
            print("Stopping the pipeline...")
            self.pipeline.send_event(Gst.Event.new_eos())
            # Wait for gstreamer to fully stop, otherwise file will be corrupted
            print("Waiting for the EOS message on the bus")
            # This method will block until the EOS message is received
            self.bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS)
        finally:
            # Stop the pipeline when done
            print("Stopping pipeline")
            self.pipeline.set_state(Gst.State.NULL)

            # save the timestamps to a file
            print(f"Gathered {len(self.ntp_timestamps)} timestamps")
            print("last timestamp", self.ntp_timestamps[-1])
            time_file = open("timestamps.txt", "w")
            for ts in self.ntp_timestamps:
                time_file.write(f"{ts}\n")
            time_file.flush()  # Ensure that data is written
            time_file.close()  # Close the file properly

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
        session.connect_after(
            "on-receiving-rtcp", RTSPPipeline.on_receiving_rtcp_callback
        )

    def on_receiving_rtcp_callback(self, session, buffer: Gst.Buffer):
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
                self.rtcp_ntp = sender_info[1]  # NTP timestamp
                self.rtcp_rtp = sender_info[2]  # RTP timestamp
            # Move to the next packet
            next_packet = rtcp_packet.move_to_next()

    def calculate_frame_timestamp(self, pad, info):
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
            rtp_diff = float(rtp_buffer.get_timestamp() - self.rtcp_rtp) / 90000.0

            # Convert the NTP time to system time (seconds and microseconds)
            self.unix_time.convert_ntp_to_datetime(self.rtcp_ntp)

            # Calculate the final timestamp
            timestamp = (
                float(self.unix_time.sec)
                + float(self.unix_time.usec) / 1000000.0
                + rtp_diff
            )
            self.ntp_timestamps.append(
                (self.rtcp_ntp, self.rtcp_rtp, rtp_buffer.get_timestamp())
            )

            print(
                f"Timestamp: {timestamp}, NTP in SR: {self.rtcp_ntp}, "
                f"RTP in SR: {self.rtcp_rtp}, RTP header timestamp: {rtp_buffer.get_timestamp()}, "
                f"Marker bit: {marker_bit}"
            )
        return Gst.PadProbeReturn.OK


pipeline = RTSPPipeline()
pipeline.start_pipeline()
