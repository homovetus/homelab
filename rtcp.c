#include <glib.h>

#include <gst/codecparsers/gsth264parser.h>
#include <gst/gst.h>
#include <gst/gstelement.h>
#include <gst/rtp/rtp.h>

#include <signal.h>
#include <stdio.h>
#include <time.h>

#define NTP_TIMESTAMP_DELTA 2208988800ULL

struct timespec ntp_to_timespec(guint64 ntp_time) {
  guint32 ntp_seconds = (ntp_time >> 32);
  guint32 ntp_fraction = ntp_time & 0xFFFFFFFF;

  struct timespec ts;
  ts.tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA;
  ts.tv_nsec = (double)ntp_fraction * 1.0e6 / (double)(1LL << 32);
  return ts;
}

typedef struct {
  GstElement *pipeline;
  GstH264NalParser *h264_nal_parser;

  guint64 rtcp_ntp;
  guint32 rtcp_rtp;
  gdouble current_frame_timestamp;
} UserData;

static UserData user_data;

/* Callback for receiving RTCP packets */
static void on_receiving_rtcp_callback(GstElement *session, GstBuffer *buffer, gpointer user_data) {
  UserData *udata = (UserData *)user_data;
  GstRTCPBuffer rtcp_buffer = {0};
  GstRTCPPacket rtcp_packet = {0};

  if (!gst_rtcp_buffer_map(buffer, GST_MAP_READ, &rtcp_buffer))
    return;

  gboolean next_packet = gst_rtcp_buffer_get_first_packet(&rtcp_buffer, &rtcp_packet);
  while (next_packet) {
    if (gst_rtcp_packet_get_type(&rtcp_packet) == GST_RTCP_TYPE_SR) {
      guint32 ssrc;
      guint32 packet_count;
      guint32 octet_count;
      guint64 last_ntp = udata->rtcp_ntp;
      gst_rtcp_packet_sr_get_sender_info(&rtcp_packet, &ssrc, &udata->rtcp_ntp, &udata->rtcp_rtp, &packet_count, &octet_count);
      // print log if difference is more than 1 second
      if (udata->rtcp_ntp - last_ntp > 1000000000) {
        struct timespec ts = ntp_to_timespec(udata->rtcp_ntp);
        g_print("Received SR NTP: %ld.%ld\n", ts.tv_sec, ts.tv_nsec);
        g_print("Received SR RTP: %u\n", udata->rtcp_rtp);
      }
    }
    next_packet = gst_rtcp_packet_move_to_next(&rtcp_packet);
  }

  gst_rtcp_buffer_unmap(&rtcp_buffer);
}

/* Calculate frame timestamp */
static GstPadProbeReturn frame_callback(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
  UserData *udata = (UserData *)user_data;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);
  GstRTPBuffer rtp_buffer = {0};

  if (!gst_rtp_buffer_map(buffer, GST_MAP_READ, &rtp_buffer)) {
    return GST_PAD_PROBE_OK;
  }

  gboolean marker_bit = gst_rtp_buffer_get_marker(&rtp_buffer);

  if (marker_bit) {
    struct timespec ts = ntp_to_timespec(udata->rtcp_ntp);
    guint32 rtp_timestamp = gst_rtp_buffer_get_timestamp(&rtp_buffer);
    gdouble rtp_diff = (gdouble)(rtp_timestamp - udata->rtcp_rtp) / 90000.0;

    gdouble timestamp = ts.tv_sec + (ts.tv_nsec / 1000000.0) + rtp_diff;
    gdouble diff = timestamp - udata->current_frame_timestamp;
    if (diff > 0.5 || diff < 0) {
      printf("diff: %lf\n", diff);
    }
    udata->current_frame_timestamp = timestamp;

    g_print("Timestamp: %lf, NTP: %llu, RTP: %u, RTP header timestamp: %u, Marker: %d\n",
            timestamp, udata->rtcp_ntp, udata->rtcp_rtp, rtp_timestamp, marker_bit);
  }

  gst_rtp_buffer_unmap(&rtp_buffer);

  return GST_PAD_PROBE_OK;
}

// Emitted after a new manager (like rtpbin) was created and the default properties were configured.
static void new_manager_callback(GstElement *rtspsrc, GstElement *manager, gpointer user_data) {
  GstPad *rtcp_pad;
  GObject *session; // RTPManager's internal session

  rtcp_pad = gst_element_request_pad_simple(manager, "recv_rtcp_sink_0");
  if (!rtcp_pad) {
    g_printerr("Failed to request recv_rtcp_sink_0 pad\n");
    return;
  }

  g_signal_emit_by_name(manager, "get-internal-session", 0, &session);
  if (!session) {
    g_printerr("Failed to get internal session\n");
    return;
  }

  g_signal_connect_after(session, "on-receiving-rtcp", G_CALLBACK(on_receiving_rtcp_callback), user_data);

  gst_object_unref(session);
}

static GstPadProbeReturn inject_sei_cb(GstPad *pad, GstPadProbeInfo *info, gpointer user_data) {
  UserData *udata = (UserData *)user_data;
  GstBuffer *buffer = GST_PAD_PROBE_INFO_BUFFER(info);
  GstBuffer *new_buffer;
  GstH264SEIMessage sei_msg;
  GstH264UserDataUnregistered *udu;
  GstMemory *sei_memory;
  GArray *sei_data;

  memset(&sei_msg, 0, sizeof(GstH264SEIMessage));
  sei_msg.payloadType = GST_H264_SEI_USER_DATA_UNREGISTERED;
  udu = &sei_msg.payload.user_data_unregistered;

  // 96dac8c1-d1cb-42e4-8981-34f229180850
  guint8 const uuid[16] = {0x96, 0xda, 0xc8, 0xc1,
                           0xd1, 0xcb,
                           0x42, 0xe4,
                           0x89, 0x81,
                           0x34, 0xf2, 0x29, 0x18, 0x08, 0x50};
  memcpy(udu->uuid, uuid, sizeof(uuid));

  // data is the last_timestamp
  udu->data = (guint8 *)&udata->current_frame_timestamp;
  udu->size = sizeof(udata->current_frame_timestamp);

  sei_data = g_array_new(FALSE, FALSE, sizeof(sei_msg));
  g_array_append_vals(sei_data, &sei_msg, 1);
  sei_memory = gst_h264_create_sei_memory_avc(4, sei_data);
  g_array_unref(sei_data);

  new_buffer = gst_h264_parser_insert_sei_avc(udata->h264_nal_parser, 4, buffer, sei_memory);
  if (new_buffer != NULL) {
    info->data = new_buffer;
    info->size = gst_buffer_get_size(new_buffer);
    gst_buffer_unref(buffer);
  }

  gst_memory_unref(sei_memory);

  return GST_PAD_PROBE_OK;
}

static void handle_sigint(int signum) {
  gst_element_send_event(user_data.pipeline, gst_event_new_eos());
}

int main_func(int argc, char *argv[]) {
  if (argc < 3) {
    g_printerr("Usage: %s <RTSP URL> <Output File Prefix>\n", argv[0]);
    return -1;
  }

  { // Initialize the GStreamer library, build gstreamer elements in UserData
    gst_init(&argc, &argv);
    gchar *pipeline_desc = g_strdup_printf("rtspsrc name=rtspsrc protocols=tcp location=%s ! "
                                           "rtpjitterbuffer name=rtpjitterbuffer ! "
                                           "rtph264depay name=rtph264depay ! "
                                           "h264parse name=h264parse ! "
                                           "splitmuxsink name=splitmuxsink location=%s%%02d.mp4 max-size-time=300000000000 max-size-bytes=500000000", // 30 minutes, 500 MB
                                           argv[1], argv[2]);
    printf("pipeline_desc: %s\n", pipeline_desc);
    user_data.pipeline = gst_parse_launch(pipeline_desc, NULL);
    g_free(pipeline_desc);
    if (!user_data.pipeline) {
      g_printerr("Pipeline can nat be created");
      return -1;
    }

    user_data.h264_nal_parser = gst_h264_nal_parser_new();
  }

  { // Connect callbacks
    GstElement *rtspsrc = gst_bin_get_by_name(GST_BIN(user_data.pipeline), "rtspsrc");
    GstElement *rtph264depay = gst_bin_get_by_name(GST_BIN(user_data.pipeline), "rtph264depay");
    GstElement *h264parse = gst_bin_get_by_name(GST_BIN(user_data.pipeline), "h264parse");
    GstPad *depaysink_pad = gst_element_get_static_pad(rtph264depay, "sink");
    GstPad *parsesrc_pad = gst_element_get_static_pad(h264parse, "src");

    g_signal_connect(rtspsrc, "new-manager", G_CALLBACK(new_manager_callback), &user_data);
    gst_pad_add_probe(depaysink_pad, GST_PAD_PROBE_TYPE_BUFFER, frame_callback, &user_data, NULL);
    gst_pad_add_probe(parsesrc_pad, GST_PAD_PROBE_TYPE_BUFFER, inject_sei_cb, &user_data, NULL);

    gst_object_unref(parsesrc_pad);
    gst_object_unref(depaysink_pad);
    gst_object_unref(h264parse);
    gst_object_unref(rtph264depay);
    gst_object_unref(rtspsrc);
  }

  { // Start the pipeline
    GstStateChangeReturn ret = gst_element_set_state(user_data.pipeline, GST_STATE_PLAYING);
    if (ret == GST_STATE_CHANGE_FAILURE) {
      g_printerr("Unable to set the pipeline to the playing state\n");
      gst_object_unref(user_data.pipeline);
      return -1;
    }
  }

  { // Configure program exit handling
    signal(SIGINT, handle_sigint);
    GstBus *bus = gst_element_get_bus(user_data.pipeline);
    GstMessage *msg = gst_bus_timed_pop_filtered(bus, GST_CLOCK_TIME_NONE, GST_MESSAGE_ERROR | GST_MESSAGE_EOS);
    if (msg != NULL) {
      GError *err;
      gchar *debug_info;

      switch (GST_MESSAGE_TYPE(msg)) {
      case GST_MESSAGE_ERROR:
        gst_message_parse_error(msg, &err, &debug_info);
        g_printerr("Error received from element %s: %s\n", GST_OBJECT_NAME(msg->src), err->message);
        g_printerr("Debugging information: %s\n", debug_info ? debug_info : "none");
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
    gst_object_unref(bus);
  }

  { // Free resources in UserData
    gst_h264_nal_parser_free(user_data.h264_nal_parser);
    gst_element_set_state(user_data.pipeline, GST_STATE_NULL);
    gst_object_unref(user_data.pipeline);
    g_print("Exiting");
  }

  return 0;
}

int main(int argc, char *argv[]) {
#if defined(__APPLE__) && TARGET_OS_MAC && !TARGET_OS_IPHONE
  return gst_macos_main((GstMainFunc)main_func, argc, argv, NULL);
#else
  return main_func(argc, argv);
#endif
}
