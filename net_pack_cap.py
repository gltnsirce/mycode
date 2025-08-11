import os
import subprocess
import time
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_output_file_name(output_file_name, interface):
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d%H%M%S")
    output_file = f"/tmp/{output_file_name}_{interface}_{timestamp}.pcap"
    return output_file

def capture_packets(output_file_name, interface):
    while True:
        print("first while Ture")
        output_file = generate_output_file_name(output_file_name, interface)

        if os.path.exists(output_file):
            logging.info(f'File {output_file} already exists, skipping')
            continue

        subprocess.call(['pktcap-uw', '--uplink', interface, '--dir', directional, '-o', output_file, '-C', pack_size])
        print("line 21 subprocess.call, Capture file size:", file_size)
        print("line 21 subprocess.call, new packet file name:", new_output_file)

        while True:
            print("second while Ture")
            time.sleep(10)
            file_size = get_file_size(output_file)
            logging.info(f'Capture file size: {file_size}')
            print("second while Ture, Capture file size:", file_size)

            if file_size >= 50 * 1024 * 1024:
                new_output_file = generate_output_file_name(output_file_name, interface)
                print("Capture file size:", file_size)
                print("new packet file name:", new_output_file)
                subprocess.call(['pktcap-uw', '--uplink', interface, '--dir', directional, '-o', new_output_file, '-C', pack_size])
                logging.info('File size exceeded 50MB, starting new capture...')

            elif file_size > 0:
                logging.info(f'Capture file: {output_file}, size: {file_size / (1024 * 1024):.2f} MB')

            else:
                logging.info(f'Capture file: {output_file}, size: 0 MB')

            current_time = datetime.now()
            time_diff = current_time - start_time

            if time_diff.total_seconds() >= 24 * 60 * 60:
                break

        subprocess.call(['pktcap-uw', '--uplink', interface, '--dir', directional, '-o', output_file, '-C', pack_size])
        logging.info('Clearing and restarting capture...')

def get_file_size(file_path):
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0

def exec_time():
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
    return timestamp

pack_size = "50"
directional = "2"
output_file_name = "network_trace"
interface = "vmnic1"
capture_packets(output_file_name, interface)