import subprocess
import time
import sys
import os

def start_process(command):
    print(f"Starting: {' '.join(command)}")
    return subprocess.Popen(command)

def main():
    bot_command = [sys.executable, "main.py"]
    dashboard_command = [sys.executable, "dashboard.py"]

    bot_process = start_process(bot_command)
    dashboard_process = start_process(dashboard_command)

    try:
        while True:
            # Check if bot crashed
            if bot_process.poll() is not None:
                print(f"[WARNING] Bot process (main.py) crashed with exit code {bot_process.returncode}. Restarting in 5 seconds...")
                time.sleep(5)
                bot_process = start_process(bot_command)

            # Check if dashboard crashed
            if dashboard_process.poll() is not None:
                print(f"[WARNING] Dashboard process (dashboard.py) crashed with exit code {dashboard_process.returncode}. Restarting in 5 seconds...")
                time.sleep(5)
                dashboard_process = start_process(dashboard_command)

            # Sleep to prevent high CPU usage in the monitoring loop
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Launcher shutting down. Terminating processes...")
        bot_process.terminate()
        dashboard_process.terminate()
        bot_process.wait()
        dashboard_process.wait()
        print("[INFO] Shutdown complete.")

if __name__ == "__main__":
    main()
