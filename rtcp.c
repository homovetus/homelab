#include <glib.h>
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

/* Callback for receiving RTCP packets */
static void on_receiving_rtcp_callback(GstPad *pad, GstPadProbeInfo *info,
                                       gpointer user_data) {
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);
  GstRTPBuffer rtp_buffer = {0};
  GstRTCPBuffer rtcp_buffer = {0};
  GstRTCPPacket rtcp_packet;

  if (!gst_rtcp_buffer_map(buffer, GST_MAP_READ, &rtcp_buffer))
    return;

  if (gst_rtcp_buffer_get_first_packet(&rtcp_buffer, &rtcp_packet)) {
    if (gst_rtcp_packet_get_type(&rtcp_packet) == GST_RTCP_TYPE_SR) {
      GstRTCPSenderInfo sender_info;
      gst_rtcp_packet_sr_get_sender_info(&rtcp_packet, &sender_info);
      rtcp_ntp = sender_info.ntptime;
      rtcp_rtp = sender_info.rtptime;
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

/* Inject SEI metadata */
static GstPadProbeReturn inject_sei(GstPad *pad, GstPadProbeInfo *info,
                                    gpointer user_data) {
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);

  GstVideoMeta *meta =
      gst_buffer_add_video_sei_user_data_unregistered_meta(buffer, 114, 51, 10);
  if (meta) {
    g_print("SEI metadata injected\n");
  }

  return GST_PAD_PROBE_OK;
}

int main_func(int argc, char *argv[]) {
  GstElement *pipeline;
  GstElement *rtspsrc, *rtpjitterbuffer, *rtph264depay, *h264parse,
      *splitmuxsink;
  GstPad *depaysink_pad, *parsesrc_pad;
  GstBus *bus;
  GMainLoop *loop;

  gst_init(&argc, &argv);

  /* Create the pipeline */
  pipeline =
      gst_parse_launch("rtspsrc name=rtspsrc protocols=tcp "
                       "location=rtsp://user:pass@127.0.0.1:8554/stream0 ! "
                       "rtpjitterbuffer name=rtpjitterbuffer ! "
                       "rtph264depay name=rtph264depay ! "
                       "h264parse name=h264parse ! "
                       "splitmuxsink name=splitmuxsink location=video%02d.mp4 "
                       "max-size-time=10000000000 max-size-bytes=1000000",
                       NULL);

  loop = g_main_loop_new(NULL, FALSE);

  /* Connect RTSP manager callbacks */
  rtspsrc = gst_bin_get_by_name(GST_BIN(pipeline), "rtspsrc");
  rtph264depay = gst_bin_get_by_name(GST_BIN(pipeline), "rtph264depay");
  depaysink_pad = gst_element_get_static_pad(rtph264depay, "sink");
  h264parse = gst_bin_get_by_name(GST_BIN(pipeline), "h264parse");
  parsesrc_pad = gst_element_get_static_pad(h264parse, "src");

  g_signal_connect(rtspsrc, "new-manager",
                   G_CALLBACK(on_receiving_rtcp_callback), NULL);
  gst_pad_add_probe(depaysink_pad, GST_PAD_PROBE_TYPE_BUFFER,
                    calculate_frame_timestamp, NULL, NULL);
  gst_pad_add_probe(parsesrc_pad, GST_PAD_PROBE_TYPE_BUFFER, inject_sei, NULL,
                    NULL);

  /* Start the pipeline */
  gst_element_set_state(pipeline, GST_STATE_PLAYING);
  g_main_loop_run(loop);

  /* Cleanup */
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
