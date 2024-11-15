import tkinter as tk
import ntplib
from datetime import datetime, timezone
import time


# Global variable to hold the latest NTP time
ntp_time_offset = 0


def query_ntp_time():
    global ntp_time_offset
    client = ntplib.NTPClient()
    try:
        # Query NTP server
        response = client.request("127.0.0.1")
        ntp_time_offset = response.tx_time - time.time()
        print(f"NTP time offset: {ntp_time_offset:.6f} seconds")
    except Exception as e:
        ntp_time_offset = None
        print(f"Error querying NTP: {e}")


def get_current_time():
    if ntp_time_offset is not None:
        # Calculate current time using the offset from the NTP time
        current_time = datetime.fromtimestamp(
            time.time() + ntp_time_offset, tz=timezone.utc
        )
    else:
        # If no NTP time, use the local system time
        current_time = datetime.now(tz=timezone.utc)
    return current_time.strftime("%H:%M:%S:%f")[:-3]


index = 1


def update_clock():
    global index
    time = get_current_time()
    time_label.config(text=time)
    if index == 1:
        time_label.config(text=get_current_time())
        index = 2
    elif index == 2:
        # time_label.config(text="                     ")
        index = 3
    elif index == 3:
        time_label.config(text="                     ")
        index = 4
    elif index == 4:
        # time_label.config(text="                     ")
        index = 1
    progress1 = int(time[-3])
    progress2 = int(time[-2])
    progress3 = int(time[-1])
    # make the correspond progress at index progress1 to be 'o'
    baseProgress1 = "----------"
    baseProgress2 = "----------"
    baseProgress3 = "----------"
    baseProgress1 = (
        baseProgress1[:progress1] + str(progress1) + baseProgress1[progress1 + 1 :]
    )
    baseProgress2 = (
        baseProgress2[:progress2] + str(progress2) + baseProgress2[progress2 + 1 :]
    )
    baseProgress3 = (
        baseProgress3[:progress3] + str(progress3) + baseProgress3[progress3 + 1 :]
    )
    progress_label1.config(text=baseProgress1)
    progress_label2.config(text=baseProgress2)
    progress_label3.config(text=baseProgress3)

    root.after(8, update_clock)  # Refresh every 8 ms, 120 FPS


def update_ntp():
    # Query the NTP server every 30 seconds
    query_ntp_time()
    root.after(30000, update_ntp)  # Refresh every 30,000 ms (30 seconds)


# Initialize the Tkinter root
root = tk.Tk()
root.title("NTP Clock")
root.configure(bg="black")  # Set background color to black

# Create a label to display the time
time_label = tk.Label(
    root, font=("Times New Roman", 250), fg="white", bg="black"
)  # Set font color to white and background to black
time_label.pack()

# Add another label for progress bar
progress_label1 = tk.Label(root, font=("Times New Roman", 200), fg="white", bg="black")
progress_label2 = tk.Label(root, font=("Times New Roman", 200), fg="white", bg="black")
progress_label3 = tk.Label(root, font=("Times New Roman", 200), fg="white", bg="black")

progress_label1.pack()
progress_label2.pack()
progress_label3.pack()

# Start the clock and NTP update loops
update_clock()
# update_ntp()

# Start the Tkinter main loop
root.mainloop()
