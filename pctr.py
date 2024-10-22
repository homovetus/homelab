import av
import os
from uuid import UUID
import struct

path = "./build/macosx/arm64/debug/d201.mp4"
container = av.open(path)

# remove extension and add .txt at the end, so we can save it in the same folder
output_name = os.path.splitext(path)[0] + ".txt"

print(f"Output name: {output_name}")

stream = container.streams.video[0]

# Loop through the packets and frames
with open(output_name, "w") as f:
    for packet in container.demux(stream):
        for frame in packet.decode():
            for sd in list(frame.side_data.keys()):
                # Convert the side data to bytes
                bts = bytes(sd)

                # Extract the first 16 bytes as UUID
                uuid_bts = bts[:16]
                uuid_str = str(UUID(bytes=uuid_bts))

                # Extract the bytes for the double data (assuming it's right after the UUID)
                double_bts = bts[16:24]  # 8 bytes for a double

                # Convert the byte data to a double using struct.unpack
                double_value = struct.unpack("d", double_bts)[0]
                print(f"{uuid_str}: {double_value}")
                f.write(f"{double_value}\n")
