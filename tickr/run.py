import subprocess
import os
import time
from subprocess import Popen
from typing import List, Dict
from loguru import logger
from rich import print
import os

# Define different environment variables for each instance
env_vars_list: List[Dict] = [
    # {"CONFIG_FILE": "tickr/configs/es.dev.json", "ID": "af2c5918-aadd-477b-ac3f-7aae52296053"},
    {"CONFIG_FILE": "tickr/configs/nq.dev.json", "ID": "9e638844-d5aa-4897-8e22-16d869e69709"},
]

scriptPath = "tickr/strategies/fibonacci/run.py"
backtestFilePath = os.path.abspath("datasets/NQ 27-02-2025.Last/NQ 27-02-2025.Last.txt")
# launchpad: List =  ["python", script_path, "production"]
launchpad: List =  ["python", scriptPath, "backtest", "--filepath", backtestFilePath]

processes = []


# Function to start a process
def start_process(env_vars):
    env = os.environ.copy()
    env.update(env_vars)
    log_file = open(f"log_task_{env_vars['ID']}.log", "w")
    process = subprocess.Popen(
        launchpad,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True
    )
    return process, log_file

if __name__ == "__main__":
    # Start all processes
    try:
        for env_vars in env_vars_list:
            process, log_file = start_process(env_vars)
            processes.append({"process": process, "env_vars": env_vars, "log_file": log_file})
        logger.success("All processes started. Press Ctrl+C to stop.")
        print(processes)

        monitoring = True
        while monitoring:
            for p in processes:
                process = p["process"]
                exit_code = process.poll()  # Check if process has finished

                if exit_code is not None:  # Process has exited
                    p["log_file"].close()

                    if exit_code == 0:
                        logger.success(f"Process with env {p['env_vars']} completed successfully.")
                        monitoring = False
                    else:
                        logger.error(f"Process with env {p['env_vars']} crashed with exit code {exit_code}.")
                        monitoring = False
            time.sleep(1)

    except KeyboardInterrupt:
        logger.warning("\nKeyboard Interrupt detected! Stopping all processes...")
        for p in processes:
            process = p["process"]
            logger.warning(f"Stopping process {p['env_vars']} (PID: {process.pid})")
            process.terminate()  # Sends SIGTERM, allowing the script to exit cleanly
            p["log_file"].close()

        logger.warning("All processes stopped.")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        for p in processes:
            process = p["process"]
            if process.poll() is None:  # If process is still running
                logger.warning(f"Forcing stop for process {p['env_vars']} (PID: {process.pid})")
                process.kill()  # Hard kill the process
                p["log_file"].close()

        logger.success("Cleanup complete. Exiting.")