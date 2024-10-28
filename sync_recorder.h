#ifndef SYNC_RECORDER_H
#define SYNC_RECORDER_H

#include <gst/codecparsers/gsth264parser.h>
#include <gst/gst.h>

#define NTP_TIMESTAMP_DELTA 2208988800ULL

struct timespec ntp_s2timespec(guint64 ntp_time) {
  guint32 ntp_seconds = (ntp_time >> 32);
  guint32 ntp_fraction = ntp_time & 0xFFFFFFFF;

  struct timespec ts;
  ts.tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA;
  ts.tv_nsec = (double)ntp_fraction * 1.0e6 / (double)(1LL << 32);
  return ts;
}

struct timespec ntp_ns2timespec(guint64 ntp_time) {
  guint64 ntp_seconds = ntp_time / 1000000000;
  guint64 ntp_nanoseconds = ntp_time % 1000000000;

  struct timespec ts;
  ts.tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA;
  ts.tv_nsec = ntp_nanoseconds;
  return ts;
}

typedef struct {
  GstElement *pipeline;
  GstH264NalParser *h264_nal_parser;

  guint64 rtcp_ntp;
  guint32 rtcp_rtp;
  gdouble current_frame_timestamp;
} UserData;

void register_rtcp_callback(GstElement *rtspsrc, GstElement *manager, gpointer user_data);
void update_rtcp_ntp(GstElement *session, GstBuffer *buffer, gpointer user_data);
GstPadProbeReturn calculate_timestamp(GstPad *pad, GstPadProbeInfo *info, gpointer user_data);
GstPadProbeReturn inject_timestamp(GstPad *pad, GstPadProbeInfo *info, gpointer user_data);

#endif
