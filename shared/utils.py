#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used across the bern3d_tools package
"""

import yaml
import subprocess
from typing import Optional, Type, TypeVar


Config = TypeVar('Config')

def read_config_file(config_file: str, config_class: Type[Config]) -> Config:
    """
    This function reads a configuration file, and fills in the attributes of the dataclass with
    the respective entries in the configuratio file

    Parameters:
    config_file (str): Path to the configuration file
    config_class (Type[Config]): The dataclass to be filled with the configuration entries

    Returns:
    Config: The dataclass with the configuration entries filled in
    """
    assert '.yaml' in config_file.lower(), "The configuration file should be a '.yaml' file"

    with open(config_file, encoding='utf-8') as file:
        config_list = yaml.load(file, Loader=yaml.FullLoader)

    config = config_class(**config_list)

    return config

def submit_job(script_template: str, executable_name: str, executable_path: str, time: str,
               header_command: Optional[str] = None,
               dependency: Optional[str] = None,
               dependency_type: Optional[str] = 'afterok',
               command_line_arg: Optional[list[str]] = None) -> str:
    """
    Submit a job using sbatch with optional dependency and iteration parameters.

    Parameters:
    script_template (str): Path to the script template.
    executable_name (str): Name of the executable.
    executable_path (str): Path to the executable.
    time (str): Time to run the script.
    header_command (str): Header command to be added to the sbatch script.
    dependency (str): Dependency job id.
    dependency_type (str): Type of dependency (afterok, afterany, other slurm option).
    command_line_arg (list): List of command line arguments.

    Returns:
    str: JobID of the submitted job.
    """
    # define command
    command = ["sbatch"]

    command.append(f"--job-name={executable_name}")
    command.append(f"--time={time}")
    command.append(f"--chdir={executable_path}")

    # check if header command is provided
    if header_command:
        command.append(header_command)

    # check if dependency is provided
    if dependency:

        if len(dependency) == 1:
            dependency_ids = dependency[0]
        else:
            dependency_ids = ":".join(dependency)

        command.append(f"--dependency={dependency_type}:{dependency_ids}")

    command.append(script_template)

    if (command_line_arg is not None) and (len(command_line_arg) > 0):
        for arg in command_line_arg:
            command.append(arg)

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]

    return job_id