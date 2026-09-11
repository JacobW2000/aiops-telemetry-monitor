import time
import psutil
import httpx

BACKEND_URL = "http://localhost:8000/api/metrics"

def get_system_snapshot():
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent

    # Get highest CPU-consuming process
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top_proc = max(processes, key=lambda p: p['cpu_percent'] or 0.0, default={'name': 'unknown', 'cpu_percent': 0.0})

    return {
        "cpu_percent": cpu,
        "memory_percent": mem,
        "disk_usage_percent": disk,
        "top_process_name": top_proc['name'],
        "top_process_cpu": float(top_proc['cpu_percent'] or 0.0)
    }
def main():
    print("Starting Telemetry Collector Daemon...")
    client = httpx.Client()

    while True:
        try:
            data = get_system_snapshot()
            client.post(BACKEND_URL, json=data)
        except Exception as e:
            print(f"Failed to post metrics: {e}")
        time.sleep(2.0)

if __name__ == "__main__":
    main()