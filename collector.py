import time
import shutil
import psutil
import requests

API_URL = "http://localhost:8000/api/metrics"

print("Starting telemetry collector... Press Ctrl+C to stop.")

while True:
    try:
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent

        # Use Python's built-in shutil to bypass the Windows C-extension bug
        try:
            disk_total, disk_used, disk_free = shutil.disk_usage("C:\\")
            disk = round((disk_used / disk_total) * 100, 1)
        except Exception:
            disk = 0.0

        top_proc = max(
            psutil.process_iter(['name', 'cpu_percent']),
            key=lambda p: p.info['cpu_percent'] or 0.0,
            default=None
        )

        proc_name = top_proc.info['name'] if top_proc else "system"
        proc_cpu = top_proc.info['cpu_percent'] if top_proc else 0.0

        payload = {
            "cpu_percent": float(cpu),
            "memory_percent": float(memory),
            "disk_usage_percent": float(disk),
            "top_process_name": str(proc_name),
            "top_process_cpu": float(proc_cpu)
        }

        response = requests.post(API_URL, json=payload)
        print(
            f"[{time.strftime('%X')}] Sent CPU: {cpu}% | RAM: {memory}% | Disk: {disk}% -> Status: {response.status_code}")
    except Exception as e:
        print(f"Error sending telemetry: {e}")

    time.sleep(2)