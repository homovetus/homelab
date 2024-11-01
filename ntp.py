def ntp2unix(ntp_time):
    NTP_TIMESTAMP_DELTA = (
        2208988800  # Difference in seconds between NTP and Unix epochs: 1900 vs 1970
    )

    # Extract seconds and fractional part from NTP timestamp
    ntp_seconds = ntp_time >> 32
    ntp_fraction = ntp_time & 0xFFFFFFFF

    # Convert seconds to system time
    tv_sec = ntp_seconds - NTP_TIMESTAMP_DELTA
    # Convert fractional part to nanoseconds
    tv_nsec = int((ntp_fraction * 1e9) / (1 << 32))

    return {"tv_sec": tv_sec, "tv_nsec": tv_nsec}


def frame_timestamp(rtcp_ntp, rtcp_rtp, frame_rtp):
    # Calculate the RTP timestamp difference (90kHz clock)
    diff = (frame_rtp - rtcp_rtp) / 90000

    # Convert NTP timestamp to system time
    ntp_timespec = ntp2unix(rtcp_ntp)
    rtcp_ntp = ntp_timespec["tv_sec"] + ntp_timespec["tv_nsec"] / 1e9

    # Frame timestamp = NTP timestamp in RTCP + RTP timestamp difference
    timestamp = rtcp_ntp + diff
    return timestamp


print(frame_timestamp(16918853004384289161, 2918953038, 2919379998))
print(frame_timestamp(16918853004384289161, 2918953038, 2919382968))


# Timestamp: the frame timestamp in Unix time
# RTCP NTP: the NTP timestamp in RTCP SR (received every 5 seconds from camera, absolute time)
# RTCP RTP: the RTP timestamp in RTCP SR (received every 5 seconds from camera, relative time)
# RTP: the RTP timestamp for the frame, which is always increasing

# Once we received a new RTCP SR, then the frame timestamp calculation will be based on new RTCP SR.
# The rewind appears when we start using new RTCP SR.

# Timestamp: 1730238639.572999, RTCP NTP: 16918853004384289161, RTCP RTP: 2918953038, RTP: 2919373968, Marker: 1
# Timestamp: 1730238639.605999, RTCP NTP: 16918853004384289161, RTCP RTP: 2918953038, RTP: 2919376938, Marker: 1
# Timestamp: 1730238639.639999, RTCP NTP: 16918853004384289161, RTCP RTP: 2918953038, RTP: 2919379998, Marker: 1
# Received RTCP SR NTP: 16918853024720959307
# Received RTCP SR RTP: 2919382968
# Timestamp: 1730238639.630999, RTCP NTP: 16918853024720959307, RTCP RTP: 2919382968, RTP: 2919382968, Marker: 1
# Timestamp: 1730238639.663999, RTCP NTP: 16918853024720959307, RTCP RTP: 2919382968, RTP: 2919385938, Marker: 1
# Timestamp: 1730238639.697999, RTCP NTP: 16918853024720959307, RTCP RTP: 2919382968, RTP: 2919388998, Marker: 1

# Timestamp: 1730387202.607999, RTCP NTP: 16919491076451043639, RTCP RTP: 1406573853, RTP: 1407022233, Marker: 1
# Received SR NTP: 1730387202.600999
# Received SR RTP: 1407025203
# Timestamp: 1730387202.600999, RTCP NTP: 16919491097818505936, RTCP RTP: 1407025203, RTP: 1407025203, Marker: 1
