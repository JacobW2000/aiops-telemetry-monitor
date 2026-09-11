from fastmcp import FastMCP
import psutil
import os

mcp = FastMCP("System-Diagnostic-Server")

@mcp.tool()
def inspect_top_processes(limit: int = 5) -> str:
    """Returns the top N processes running on the machine sorted by memory and CPU usage."""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    sorted_procs = sorted(procs, key=lambda x: (x['cpu_percent'] or 0.0), reverse=True)[:limit]

    output = "PID\tName\t\tCPU%\tMemory%\n"
    output += "-" * 40 + "\n"
    for p in sorted_procs:
        output += f"{p['pid']}\t{p['name'][:12]}\t\t{p['cpu_percent']}\t{p['memory_percent']:.1f}\n"
    return output

@mcp.tool()
def get_system_load() -> str:
    """Returns overall system performance summary including CPU core count, load averages, and memory."""
    cpu_count = psutil.cpu_count(logical=True)
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else ("N/A", "N/A", "N/A")
    mem = psutil.virtual_memory()

    return (
        f"CPU Cores: {cpu_count}\n"
        f"Load Average (1m, 5m, 15m): {load_avg}\n"
        f"Total RAM: {mem.total / (1024**3):.2f} GB\n"
        f"Used RAM: {mem.used / (1024**3):.2f} GB ({mem.percent}%)\n"
    )

@mcp.tool()
def read_tail_logs(lines: int = 20) -> str:
    """Reads recent system log entries to assist with anomaly root cause identification."""
    log_file = "/var/log/syslog" if os.path.exists("/var/log/syslog") else "/var/log/system.log"
    if not os.path.exists(log_file):
        return "System log file not directly accessible."

    try:
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8001)