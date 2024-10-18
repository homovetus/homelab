#include <glib.h>
#include <gst/codecparsers/gsth264parser.h>
#include <gst/gst.h>
#include <gst/rtp/rtp.h>
#include <gst/video/video.h>
#include <stdio.h>
#include <sys/time.h>

static guint64 rtcp_ntp = 0;
static guint32 rtcp_rtp = 0;
static GMainLoop *loop;

/* UnixTime equivalent structure for C */
typedef struct {
  gint sec;
  gint usec;
} UnixTime;

static UnixTime unix_time;

/* Helper to convert NTP to datetime */
void convert_ntp_to_datetime(guint64 ntp_timestamp) {
  if (ntp_timestamp > 0) {
    guint32 ntp_seconds = (ntp_timestamp >> 32);
    guint32 ntp_fraction = ntp_timestamp & 0xFFFFFFFF;
    unix_time.sec = ntp_seconds - 2208988800U; // Convert NTP to Unix time
    unix_time.usec = (ntp_fraction * 1000000ULL) >> 32;
  }
}

// Emitted after a new manager (like rtpbin) was created and the default
// properties were configured.
static void new_manager_callback(GstElement *rtspsrc, GstElement *manager,
                                 gpointer udata);

/* Callback for receiving RTCP packets */
static void on_receiving_rtcp_callback(GstElement *session, GstBuffer *buffer,
                                       gpointer udata) {
  GstRTCPBuffer rtcp_buffer = {0};
  GstRTCPPacket rtcp_packet;

  if (!gst_rtcp_buffer_map(buffer, GST_MAP_READ, &rtcp_buffer))
    return;

  if (gst_rtcp_buffer_get_first_packet(&rtcp_buffer, &rtcp_packet)) {
    if (gst_rtcp_packet_get_type(&rtcp_packet) == GST_RTCP_TYPE_SR) {
      guint32 ssrc;
      guint32 packet_count;
      guint32 octet_count;
      gst_rtcp_packet_sr_get_sender_info(&rtcp_packet, &ssrc, &rtcp_ntp,
                                         &rtcp_rtp, &packet_count,
                                         &octet_count);
    }
  }

  gst_rtcp_buffer_unmap(&rtcp_buffer);
}

/* Calculate frame timestamp */
static GstPadProbeReturn calculate_frame_timestamp(GstPad *pad,
                                                   GstPadProbeInfo *info,
                                                   gpointer user_data) {
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);
  GstRTPBuffer rtp_buffer = {0};

  if (!gst_rtp_buffer_map(buffer, GST_MAP_READ, &rtp_buffer)) {
    return GST_PAD_PROBE_OK;
  }

  gboolean marker_bit = gst_rtp_buffer_get_marker(&rtp_buffer);

  if (marker_bit) {
    guint32 rtp_timestamp = gst_rtp_buffer_get_timestamp(&rtp_buffer);
    gdouble rtp_diff = (gdouble)(rtp_timestamp - rtcp_rtp) / 90000.0;

    convert_ntp_to_datetime(rtcp_ntp);

    gdouble timestamp = unix_time.sec + (unix_time.usec / 1000000.0) + rtp_diff;

    g_print("Timestamp: %lf, NTP: %llu, RTP: %u, RTP header timestamp: %u, "
            "Marker: %d\n",
            timestamp, rtcp_ntp, rtcp_rtp, rtp_timestamp, marker_bit);
  }

  gst_rtp_buffer_unmap(&rtp_buffer);

  return GST_PAD_PROBE_OK;
}

static void new_manager_callback(GstElement *rtspsrc, GstElement *manager,
                                 gpointer udata) {
  g_print("New manager created\n");
  GstPad *rtcp_pad =
      gst_element_request_pad_simple(manager, "recv_rtcp_sink_0");
  if (!rtcp_pad) {
    g_printerr("Failed to request recv_rtcp_sink_0 pad\n");
    return;
  }
  GObject *session;
  g_signal_emit_by_name(manager, "get-internal-session", 0, &session);
  if (!rtcp_pad) {
    g_printerr("Failed to get internal session\n");
    return;
  }
  g_signal_connect_after(session, "on-receiving-rtcp",
                         G_CALLBACK(on_receiving_rtcp_callback), NULL);
}

/* Inject SEI metadata */
static GstPadProbeReturn inject_sei(GstPad *pad, GstPadProbeInfo *info,
                                    gpointer user_data) {
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);

  // GstVideoMeta *meta =
  //     gst_buffer_add_video_sei_user_data_unregistered_meta(buffer, 114, 51,
  //     10);
  // if (meta) {
  //   g_print("SEI metadata injected\n");
  // }

  return GST_PAD_PROBE_OK;
}

int main_func(int argc, char *argv[]) {
  // Initialize the GStreamer library
  gst_init(&argc, &argv);

  GstElement *pipeline = gst_parse_launch(
      "rtspsrc name=rtspsrc protocols=tcp "
      "location=rtsp://user:pass@127.0.0.1:8554/stream0 ! "
      "rtpjitterbuffer name=rtpjitterbuffer ! "
      "rtph264depay name=rtph264depay ! "
      "h264parse name=h264parse ! "
      "splitmuxsink name=splitmuxsink location=recording%02d.mp4 "
      "max-size-time=10000000000 max-size-bytes=1000000",
      NULL);
  if (!pipeline) {
    g_printerr("Pipeline can nat be created");
    return -1;
  }

  loop = g_main_loop_new(NULL, FALSE);

  GstElement *rtspsrc = gst_bin_get_by_name(GST_BIN(pipeline), "rtspsrc");
  GstElement *rtph264depay =
      gst_bin_get_by_name(GST_BIN(pipeline), "rtph264depay");
  GstPad *depaysink_pad = gst_element_get_static_pad(rtph264depay, "sink");
  GstElement *h264parse = gst_bin_get_by_name(GST_BIN(pipeline), "h264parse");
  GstPad *parsesrc_pad = gst_element_get_static_pad(h264parse, "src");

  g_signal_connect(rtspsrc, "new-manager", G_CALLBACK(new_manager_callback),
                   NULL);
  gst_pad_add_probe(depaysink_pad, GST_PAD_PROBE_TYPE_BUFFER,
                    calculate_frame_timestamp, NULL, NULL);
  // gst_pad_add_probe(parsesrc_pad, GST_PAD_PROBE_TYPE_BUFFER, inject_sei,
  // NULL,
  //                   NULL);

  /* Start the pipeline */
  GstStateChangeReturn ret = gst_element_set_state(pipeline, GST_STATE_PLAYING);
  if (ret == GST_STATE_CHANGE_FAILURE) {
    g_printerr("Unable to set the pipeline to the playing state\n");
    gst_object_unref(pipeline);
    return -1;
  }
  g_main_loop_run(loop);

  GstBus *bus = gst_element_get_bus(pipeline);
  GstMessage *msg = gst_bus_timed_pop_filtered(
      bus, GST_CLOCK_TIME_NONE, GST_MESSAGE_ERROR | GST_MESSAGE_EOS);
  if (msg != NULL) {
    GError *err;
    gchar *debug_info;

    switch (GST_MESSAGE_TYPE(msg)) {
    case GST_MESSAGE_ERROR:
      gst_message_parse_error(msg, &err, &debug_info);
      g_printerr("Error received from element %s: %s\n",
                 GST_OBJECT_NAME(msg->src), err->message);
      g_printerr("Debugging information: %s\n",
                 debug_info ? debug_info : "none");
      g_clear_error(&err);
      g_free(debug_info);
      break;
    case GST_MESSAGE_EOS:
      g_print("End-Of-Stream reached.\n");
      break;
    default:
      // Unreachable, only requested message types are ERROR and EOS
      g_printerr("Unexpected message received.\n");
      break;
    }
    gst_message_unref(msg);
  }

  /* Cleanup */
  gst_object_unref(bus);
  gst_element_set_state(pipeline, GST_STATE_NULL);
  gst_object_unref(pipeline);
  g_main_loop_unref(loop);
  return 0;
}

int main(int argc, char *argv[]) {
#if defined(__APPLE__) && TARGET_OS_MAC && !TARGET_OS_IPHONE
  return gst_macos_main((GstMainFunc)main_func, argc, argv, NULL);
#else
  return main_func(argc, argv);
#endif
}
