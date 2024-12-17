#ifndef RECORDER_H
#define RECORDER_H

#include <gst/codecparsers/gsth264parser.h>
#include <gst/gst.h>

#define NTP_TIMESTAMP_DELTA 2208988800ULL

static inline struct timespec ntp_s2timespec(guint64 ntp_time) {
  guint32 ntp_seconds = (ntp_time >> 32);
  guint32 ntp_fraction = ntp_time & 0xFFFFFFFF;

  struct timespec ts;
  ts.tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA;
  ts.tv_nsec = (double)ntp_fraction * 1.0e6 / (double)(1LL << 32);
  return ts;
}

static inline struct timespec ntp_ns2timespec(guint64 ntp_time) {
  guint64 ntp_seconds = ntp_time / 1000000000;
  guint64 ntp_nanoseconds = ntp_time % 1000000000;

  struct timespec ts;
  ts.tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA;
  ts.tv_nsec = ntp_nanoseconds;
  return ts;
}

typedef struct RTPTimeinfo {
  gdouble unix_timestamp;
  guint64 rtcp_ntp;
  guint32 rtcp_rtp;
  guint32 frame_rtp;
} RTPTimeInfo;

typedef struct {
  GstElement *pipeline;
  GstH264NalParser *h264_nal_parser;

  RTPTimeInfo time_meta;
} UserData;

void register_rtcp_callback(GstElement *rtspsrc, GstElement *manager, gpointer user_data);
void update_rtcp_ntp(GstElement *session, GstBuffer *buffer, gpointer user_data);
GstPadProbeReturn calculate_timestamp(GstPad *pad, GstPadProbeInfo *info, gpointer user_data);
GstPadProbeReturn inject_timestamp(GstPad *pad, GstPadProbeInfo *info, gpointer user_data);
gchararray generate_file_name(GstElement *splitmux, guint fragment_id, gpointer user_data);

#endif
