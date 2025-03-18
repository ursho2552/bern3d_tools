#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Wrapper script to compress netcdf files.
Author: Urs Hofmann Elizondo
Date: 12-02-2025
"""

import sys
import os
import argparse
import subprocess
from datetime import datetime
from multiprocessing import Process, Queue

# Function to log messages
def log_message(message: str, config: argparse.Namespace) -> None:
    """
    Function to log messages to a file.
    """

    input_directory = config.input_directory

    with open(os.path.join(input_directory, 'nczip_log'), 'a', encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}: {message}\n")

# Function to compress and check files
def process_file(file: str, queue: Queue, config: argparse.Namespace) -> None:
    """
    Function to compress and check a single netcdf file.
    """

    log_message(f"Processing {file}", config)

    input_directory = config.input_directory
    nczip_script = config.nczip_script
    ncequal_script = config.ncequal_script
    varnum = config.varnum

    # Run nczip script
    nczip_command = f"bash {nczip_script} -k {file}"
    nczip_result = subprocess.run(nczip_command, shell=True, check=False)
    if nczip_result.returncode != 0:
        log_message(f"nczip: Error code {nczip_result.returncode} while processing {file}", config)
        queue.put(False)
        return

    # Run ncequal script
    zipfilename = file[:-1] + 'z'
    ncequal_command = f"{ncequal_script} --variable_number {varnum} {file} {zipfilename}"
    with open(os.path.join(input_directory, 'nczip_log'), 'a', encoding="utf-8") as log_file:
        ncequal_result = subprocess.run(ncequal_command, shell=True,
                                        check=False, stdout=log_file,
                                        stderr=log_file)
    if ncequal_result.returncode != 0:
        log_message(f"ncequal returned inequality of files {file} and {zipfilename}", config)
        queue.put(False)
        return

    # Replace original file with compressed file
    os.rename(zipfilename, file)
    queue.put(True)

# Main function
def main(config: argparse.Namespace) -> None:
    """
    Main function to compress all netcdf files in the input directory.
    """

    input_directory = config.input_directory

    # Collect all files to process
    files_to_process = []
    for file in os.listdir(input_directory):
        if file.endswith('.nc'):
            files_to_process.append(os.path.join(input_directory, file))

    # Process files in parallel (should work as is)
    processes = []
    queue: Queue = Queue()
    for file in files_to_process:
        p = Process(target=process_file, args=(file, queue, config))
        processes.append(p)
        p.start()

    # Wait for all processes to finish
    for p in processes:
        p.join()

    # Check results and log final message
    results = [queue.get() for _ in processes]
    if all(results):
        log_message("finished zipping all files", config)
    else:
        log_message("compression job encountered errors", config)

if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Compress .nc files in a give directory')
    parser.add_argument('--input_directory', required=True, type=str,
                        help='Directory containing .nc files to compress')
    parser.add_argument('--nczip_script', required=False, nargs='?',
                        const='/users/uhofmann/nczip_wrapper/nczip.sh',
                        default='/users/uhofmann/nczip_wrapper/nczip.sh',
                        type=str, help='Path to nczip script')
    parser.add_argument('--ncequal_script', required=False, nargs='?',
                        const='/users/uhofmann/nczip_wrapper/ncequal.py',
                        default='/users/uhofmann/nczip_wrapper/ncequal.py',
                        type=str, help='Path to ncequal script')
    parser.add_argument('--varnum', required=False, default=3, type=int,
                        help='Number of variables to test')

    CONFIG = parser.parse_args()
    # check if scripts exists
    if not os.path.exists(CONFIG.nczip_script):
        print(f"Script file {CONFIG.nczip_script} does not exist.")
        sys.exit(1)
    if not os.path.exists(CONFIG.ncequal_script):
        print(f"Script file {CONFIG.ncequal_script} does not exist.")
        sys.exit(1)

    # check
    if not os.path.exists(CONFIG.input_directory):
        print(f"Directory {CONFIG.input_directory} does not exist.")
        sys.exit(1)

    # get a list of subdirectories that contain .nc files
    directories = []
    for root, dirs, files in os.walk(CONFIG.input_directory):
        for current_file in files:
            if current_file.endswith(".nc"):
                print(f"Found file {current_file} in {root}")
                directories.append(root)
                break

    # remove duplicates
    directories = list(set(directories))
    for directory in directories:
        print(f"Processing directory {directory}")
        CONFIG.input_directory = directory
        main(CONFIG)
        print(f"Finished processing directory {directory}")
