import csv
import os
import paramiko
import socket
import datetime
import ping3

from ping3 import ping

def check_latency(node):
    response_time = ping(node)
    return response_time

def backup_files(node, files_to_backup, ssh_key_path, remote_backup_path):
    # Connect to the node using SSH
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    private_key = paramiko.RSAKey.from_private_key_file(ssh_key_path)

    try:
        ssh.connect(node, username='your_username', pkey=private_key)
        
        # Create a temporary directory for backup files on the remote node
        remote_tmp_backup_dir = os.path.join(remote_backup_path, f"backup_{node}")
        ssh.exec_command(f"mkdir -p {remote_tmp_backup_dir}")

        # Copy files to the remote temporary backup directory
        for file_path in files_to_backup:
            scp = ssh.open_sftp()
            remote_file_path = os.path.join(remote_tmp_backup_dir, os.path.basename(file_path))
            scp.put(file_path, remote_file_path)
            scp.close()

        # Create a tar.gz archive of the remote backup files
        remote_backup_filename = f"backup_{node}.tar.gz"
        ssh.exec_command(f"tar -czf {remote_backup_filename} -C {remote_tmp_backup_dir} .")

        # Download the tar.gz archive to your localhost
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        local_backup_filename = f"backup_{node}_{timestamp}.tar.gz"
        scp = ssh.open_sftp()
        scp.get(os.path.join(remote_tmp_backup_dir, remote_backup_filename), local_backup_filename)
        scp.close()

        # Clean up remote temporary files
        ssh.exec_command(f"rm -rf {remote_tmp_backup_dir} {remote_backup_filename}")

        print(f"Backup completed for node {node}")

    except paramiko.AuthenticationException:
        print(f"Authentication failed for node {node}")
    except paramiko.SSHException as e:
        print(f"SSH error for node {node}: {str(e)}")
    finally:
        ssh.close()

def check_service(node, service, port):
    try:
        with socket.create_connection((node, port), timeout=5):
            print(f"Service {service} is running on node {node}")
            return True
    except (socket.timeout, ConnectionRefusedError):
        print(f"Service {service} is not running on node {node}")
        return False

def main():
    nodes = []
    with open('nodes_ips.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            node, ip = row
            nodes.append({'node': node, 'ip': ip})

    files_to_backup = []
    with open('files_to_backup.txt', 'r') as file:
        files_to_backup = [line.strip() for line in file.readlines()]

    services_and_ports = []
    with open('services_and_ports.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            node, service, port = row
            services_and_ports.append({'node': node, 'service': service, 'port': int(port)})

    ssh_key_path = '/path/to/your/ssh/key/id_rsa'
    remote_backup_path = '/path/to/remote/backup/directory'

    for node_info in nodes:
        node = node_info['node']
        ip = node_info['ip']
        services_on_node = [service_info for service_info in services_and_ports if service_info['node'] == node]
        files_to_backup_on_node = [file.split(',')[1] for file in files_to_backup if node == file.split(',')[0]]

        print(f"Checking network latency for node {node} ({ip})")
        latency = check_latency(ip)
        print(f"Network latency for node {node}: {latency} ms")

        print(f"Backing up files for node {node}")
        backup_files(node, files_to_backup_on_node, ssh_key_path, remote_backup_path)

        for service_info in services_on_node:
            service = service_info['service']
            port = service_info['port']
            check_service(ip, service, port)

        print("-----------------------------------")

if __name__ == "__main__":
    main()
