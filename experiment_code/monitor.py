import psutil
import socket
from datetime import datetime
import sys

if len(sys.argv) != 3:
    print("Usage: python monitor.py <log_file> <interval_in_seconds>")
    sys.exit(1)

LOG_FILE = sys.argv[1]
INTERVAL = int(sys.argv[2])

hostname = socket.gethostname()

f = open(LOG_FILE, "a")
f.write("timestamp,unix_time,hostname,cpu_percent,mem_percent\n")  # header (optional)

try:
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unix_time = datetime.now().timestamp()
        cpu_usage = psutil.cpu_percent(interval=INTERVAL)
        mem = psutil.virtual_memory()
        mem_usage = mem.percent

        log_line = f"{timestamp},{unix_time},{hostname},{cpu_usage},{mem_usage}\n"
        f.write(log_line)
        f.flush()  # ensure data is written immediately
except KeyboardInterrupt:
    print("Monitoring stopped by user.")