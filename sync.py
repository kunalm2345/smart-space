import paramiko
import threading

# List of Raspberry Pi IP addresses and their SSH credentials
raspberry_pis = [
    {'host': 'ss1.local', 'username': 'ss1', 'password': 'smartspace'},
    {'host': 'ss2.local', 'username': 'ss2', 'password': 'smartspace'},
]

# Command to run on each Raspberry Pi

def execute_command_on_pi(pi, command):
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the Raspberry Pi
        ssh.connect(pi['host'], username=pi['username'], password=pi['password'])

        # Execute the command
        stdin, stdout, stderr = ssh.exec_command(command)

        # Print the output
        print(f"Output from {pi['host']}: {stdout.read().decode().strip()}")
        print(f"Errors from {pi['host']}: {stderr.read().decode().strip()}")

        # Close the connection
        ssh.close()
    except Exception as e:
        print(f"Failed to connect to {pi['host']}: {e}")

# Create and start threads for each Raspberry Pi
def run_command(raspberry_pis, command):
    threads = []
    for pi in raspberry_pis:
        thread = threading.Thread(target=execute_command_on_pi, args=(pi,command,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    print("Command executed on all Raspberry Pis.")

while True:
    command = input("Enter command: ")
    if command == "stop sync":
        break
    run_command(raspberry_pis, command)
