import multiprocessing
import os
import sys
import time


def generate_cpu_load():
    """Infinite loop executing continuous arithmetic calculations to saturate a CPU core."""
    while True:
        _ = [i ** 2 for i in range(10_000_000)]


if __name__ == "__main__":
    cores = os.cpu_count() or 4
    print(f"Spawning heavy CPU stress processes across all {cores} cores...")
    print("Process target name: heavy_worker.py")

    workers = []
    for _ in range(cores):
        p = multiprocessing.Process(target=generate_cpu_load, daemon=True)
        p.start()
        workers.append(p)

    try:
        for p in workers:
            p.join()
    except KeyboardInterrupt:
        print("\nStopping all stress worker processes...")
        for p in workers:
            p.terminate()
        sys.exit(0)