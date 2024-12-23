import socket
import time
import sys
import subprocess

def wait_for_service(host, port, timeout=60):
    """Wait until the specified service is available on the given host and port."""
    start_time = time.time()
    while True:
        try:
            # Try to connect to the specified host and port
            with socket.create_connection((host, port), timeout=1):
                print(f"Service at {host}:{port} is available.")
                return True
        except (socket.timeout, socket.error):
            # If the connection fails, print a message and retry
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print(f"Timed out waiting for {host}:{port}.")
                return False
            print(f"Waiting for {host}:{port}... (elapsed time: {elapsed_time:.2f}s)")
            time.sleep(1)

def run_command(cmd):
    """Execute the specified command."""
    try:
        subprocess.run(cmd, check=True)
        print(f"Command '{' '.join(cmd)}' executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")

if __name__ == "__main__":
    # Get the host, port, and command to run from the script arguments
    if len(sys.argv) < 4:
        print("Usage: python wait_for_service.py <host> <port> <command> [args...]")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    cmd = sys.argv[3:]

    # Wait for the service to be available
    if wait_for_service(host, port):
        # Once the service is available, run the specified command
        run_command(cmd)
    else:
        print("Could not connect to the service.")
        sys.exit(1)
