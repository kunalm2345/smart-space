import argparse
import subprocess
import sys
import os
import shutil
import time

# Define the list of hosts and credentials
HOSTS = [
    {"hostname": "ss1.local", "username": "smartspace1", "password": "smartspace"},
    {"hostname": "ss2.local", "username": "smartspace2", "password": "smartspace"},
    {"hostname": "ss3.local", "username": "smartspace3", "password": "smartspace"},
    {"hostname": "ss4.local", "username": "smartspace4", "password": "smartspace"},
    {"hostname": "ss5.local", "username": "smartspace5", "password": "smartspace"},
    {"hostname": "ss6.local", "username": "smartspace6", "password": "smartspace"},
    {"hostname": "ss7.local", "username": "smartspace7", "password": "smartspace"},
    {"hostname": "ss8.local", "username": "smartspace8", "password": "smartspace"},
    {"hostname": "ss9.local", "username": "smartspace9", "password": "smartspace"},
    {"hostname": "ss10.local", "username": "smartspace10", "password": "smartspace"},
    {"hostname": "ss11.local", "username": "smartspace11", "password": "smartspace"},
    {"hostname": "ss12.local", "username": "smartspace12", "password": "smartspace"},
    {"hostname": "ss13.local", "username": "smartspace13", "password": "smartspace"},
]

def create_gnome_terminal_command():
    """
    Creates a gnome-terminal command that opens all SSH sessions in tabs
    """
    base_command = ["gnome-terminal", "--tab"]
    
    for i, host in enumerate(HOSTS):
        ssh_command = f"ssh {host['username']}@{host['hostname']} 'cd smart-space && python3 new_running_client.py'"
        if i == 0:
            # First tab is opened differently
            base_command.extend(["--", "bash", "-c", f"{ssh_command}"])
        else:
            # Additional tabs
            base_command.extend(["--tab", "--", "bash", "-c", f"{ssh_command}"])
    
    return base_command

def start_all_clients():
    """
    Opens all SSH sessions in tabs of a single terminal window
    """
    if not shutil.which("gnome-terminal"):
        print("Error: gnome-terminal is required. Please install it using:")
        print("sudo apt-get install gnome-terminal")
        sys.exit(1)

    try:
        command = create_gnome_terminal_command()
        subprocess.Popen(
            command,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("Launched all SSH sessions in tabs. Exiting...")
    except Exception as e:
        print(f"Error launching terminal: {str(e)}")
        sys.exit(1)

def stop_all_clients():
    """
    Stops all running client processes by sending Ctrl+C and closing the terminals
    """
    try:
        # Get all SSH processes for our hostnames
        for host in HOSTS:
            # Kill any existing SSH sessions to this host
            hostname = host['hostname']
            username = host['username']
            
            # Find and kill the SSH process
            ps_command = f"ps aux | grep 'ssh {username}@{hostname}' | grep -v grep"
            ps_output = subprocess.getoutput(ps_command)
            
            if ps_output:
                print(f"Stopping session for {hostname}...")
                # Extract PID and send SIGINT (Ctrl+C)
                pid = ps_output.split()[1]
                try:
                    subprocess.run(['kill', '-SIGINT', pid])
                except subprocess.CalledProcessError:
                    print(f"Warning: Could not send SIGINT to process {pid}")

        # Close all gnome-terminal windows running our SSH sessions
        pkill_command = "pkill -f 'gnome-terminal.*smart-space.*new_running_client.py'"
        subprocess.run(pkill_command, shell=True)
        
        print("Stopped all client sessions.")
        
    except Exception as e:
        print(f"Error stopping clients: {str(e)}")
        sys.exit(1)

def sync_time():
    """
    Synchronizes date, time, and timezone of all hosts with the current system
    """
    # Get current system's timezone
    local_timezone = subprocess.getoutput('timedatectl show --property=Timezone --value')
    # Get current system's date and time in a format suitable for the date command
    local_datetime = subprocess.getoutput('date "+%Y-%m-%d %H:%M:%S.%N"')
    
    for host in HOSTS:
        try:
            hostname = host['hostname']
            username = host['username']
            password = host['password']
            
            # Command to handle sudo with password
            sudo_prefix = f"echo {password} | sudo -S"
            
            # Set timezone first
            timezone_cmd = f"{sudo_prefix} timedatectl set-timezone {local_timezone}"
            ssh_cmd = f"ssh {username}@{hostname} '{timezone_cmd}'"
            subprocess.run(ssh_cmd, shell=True, stderr=subprocess.PIPE)
            
            # Set date and time
            time_cmd = f"{sudo_prefix} date -s '{local_datetime}'"
            ssh_cmd = f"ssh {username}@{hostname} '{time_cmd}'"
            subprocess.run(ssh_cmd, shell=True, stderr=subprocess.PIPE)
            
            # Get the synchronized time from the remote host to confirm
            verify_cmd = "date '+%Y-%m-%d %H:%M:%S %Z'"
            ssh_cmd = f"ssh {username}@{hostname} '{verify_cmd}'"
            synced_time = subprocess.getoutput(ssh_cmd)
            
            print(f"{hostname} sync'd to {synced_time}")
            
        except Exception as e:
            print(f"Error syncing time on {hostname}: {str(e)}")

def login_bitsnet(username, password):
    """
    Logs into BITS network on all Pis and verifies connection
    """
    # Login script as a Python string with proper escaping
    login_script = f'''
import requests
import xml.etree.ElementTree as ElementTree

headers = {{
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://campnet.bits-goa.ac.in:8090/httpclient.html',
    'Connection': 'keep-alive',
}}

data = {{
    'mode': '191',
    'username': '{username}',
    'password': '{password}',
    'a': '1669121329680',
    'producttype': '0',
}}

try:
    response = requests.post('https://campnet.bits-goa.ac.in:8090/login.xml', headers=headers, data=data)
    status_code = response.status_code
    root = ElementTree.fromstring(response.content)
    success = False
    for log in root.iter('message'):
        if 'signed' in log.text:
            success = True
            break
    
    # Check internet connectivity
    ping_result = subprocess.run(['ping', '-c', '1', 'google.com'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE)
    ping_success = ping_result.returncode == 0
    
    print(f"Status Code: {{status_code}}")
    print(f"Login Success: {{success}}")
    print(f"Internet Connection: {{ping_success}}")
except Exception as e:
    print(f"Error: {{str(e)}}")
'''

    for host in HOSTS:
        try:
            hostname = host['hostname']
            username_ssh = host['username']
            
            print(f"\nConnecting to {hostname}...")
            
            # Save the script to a temporary file on the remote host and execute it
            ssh_cmd = f"""ssh {username_ssh}@{hostname} 'python3 -c "{login_script}"'"""
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            
            print(result.stdout)
            if result.stderr:
                print(f"Errors: {result.stderr}")
                
        except Exception as e:
            print(f"Error on {hostname}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Control script for smart-space clients")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--start", choices=["all"], nargs="?", const="all", 
                      help="Start clients (if used without value, defaults to 'all')")
    group.add_argument("--stop", action="store_true",
                      help="Stop all running clients and close their terminals")
    group.add_argument("--synctime", action="store_true",
                      help="Synchronize date, time, and timezone of all hosts with this system")
    group.add_argument("--login", nargs=2, metavar=('USERNAME', 'PASSWORD'),
                      help="Login to BITS network on all Pis. Usage: --login username password")
    
    args = parser.parse_args()
    
    if args.start:
        start_all_clients()
    elif args.stop:
        stop_all_clients()
    elif args.synctime:
        sync_time()
    elif args.login:
        login_bitsnet(args.login[0], args.login[1])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()