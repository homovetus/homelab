import matplotlib.pyplot as plt
import numpy as np

with open("time_deltas_ocr.txt", "r") as f:
    # Extract and filter the data with a single split
    x = []
    y = []
    for line in f:
        parts = line.split(": ")
        frame_number = int(parts[0])
        timedelta = float(parts[-1])

        # Apply the filter for timedelta values
        if -1 <= timedelta <= 1:
            x.append(frame_number / 29)  # 29 FPS for camera
            y.append(timedelta * 1000)  # s to ms

print(f"Collected {len(x)} frames")

# get absolute values and the mean using abs
time_deltas_abs = [abs(delta) for delta in y]
absmean = sum(time_deltas_abs) / len(time_deltas_abs)
print(f"Mean of absolute time difference: {absmean:.2f} ms")
mean = sum(y) / len(y)
print(f"Mean of time difference: {mean:.2f} ms")

# Define the window size for moving average
window_size = 29

# Calculate moving average
moving_average = np.convolve(y, np.ones(window_size) / window_size, mode="valid")

# Adjust x to match the length of the moving average
x_moving_average = x[window_size - 1 :]  # Since moving average reduces data points

# Plot the original data and the moving average
plt.figure(figsize=(10, 6))

# Plot the original data
plt.plot(x, y, label="Original Data", alpha=0.5, color="blue")

# Plot the moving average
plt.plot(
    x_moving_average,
    moving_average,
    label=f"Moving Average (Window={window_size} FPS)",
    color="red",
)

# Add labels and title
plt.xlabel("Seconds")
plt.ylabel("Time Delta (ms)")
plt.title("OCR Time Deltas")
plt.legend()

# Add mean line
plt.axhline(y=mean, color="orange", linestyle="--", label="Mean")

# Show the plot
plt.show()
