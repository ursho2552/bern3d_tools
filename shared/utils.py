#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used across the bern3d_tools package
"""
import os
import getpass
import yaml
import logging
import subprocess
import glob
import shutil
import re
from pathlib import Path
from typing import Optional, Union, Type, TypeVar


Config = TypeVar('Config')

def get_user_email() -> str:
    """
    Get the email address of the user.

    Returns:
    str: The email address of the user
    """

    username = getpass.getuser()
    address = f"{username}@campus.unibe.ch"
    logging.info(f"Using {address} as email address for job notifications")

    return address

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

def copy_template_files(exec_name: str, new_name: str,
                        template_dir: Path, work_dir: Path) -> None:

    """
    Copy only the necessary model files for a specific executable.

    Parameters:
    exec_name (str): Name of the executable.
    template_dir (Path): Path to the template directory.
    work_dir (Path): Path to the work directory.

    Returns:
    None
    """

    # Detect all executables in the template directory
    exec_names = [
        f.name for f in template_dir.iterdir()
        if f.is_file() and os.access(f, os.X_OK)
    ]

    copied_files = []
    for file in template_dir.iterdir():
        if not file.is_file():
            continue
        name = file.name

        # Skip Slurm logs, shell scripts, and output files
        if name.startswith("slurm") and name.endswith(".out"):
            continue
        if name.endswith(".sh") or name.endswith(".out"):
            continue

        # Skip files belonging to other executables
        if any(name.startswith(prefix) for prefix in exec_names if prefix != exec_name):
            continue

        # Ignore parameter files in case executable is not present
        if name.endswith('parameter') and not name.startswith(exec_name):
            continue

        # Determine destination filename
        if name.startswith(exec_name):
            # rename file itself
            new_filename = name.replace(exec_name, new_name, 1)
        else:
            new_filename = name

        # Copy if shared or specific to exec_name
        if name.startswith(exec_name) or not any(name.startswith(prefix) for prefix in exec_names):
            dest = work_dir / new_filename
            if dest.exists():
                logging.warning(f"File already exists, not copying: {name} -> {new_filename}")
                continue
            shutil.copy2(file, dest)
            copied_files.append(dest)
            logging.warning(f"Copied: {name} -> {new_filename}")

    # Replacement within text files
    for file_path in copied_files:
        try:
            text = file_path.read_text()
        except (UnicodeDecodeError, OSError):
            # Skip binary or unreadable files
            continue
        if exec_name in text:
            new_text = text.replace(exec_name, new_name)
            file_path.write_text(new_text)
            logging.warning(f"Replaced '{exec_name}' with '{new_name}' in: {file_path.name}")

def setup_run_directory(template_dir: str, executable_name: str,
                        new_name: str, work_dir: str,
                        restart_files: str,
                        separate: bool = False) -> str:

    """
    Set up the run directory for a new simulation.

    Parameters:
    template_dir (str): Path to the template directory.
    executable_name (str): Name of the Bern3D executable.
    new_name (str): New name for the simulation.
    work_dir (str): Path to the work directory.
    restart_files (str): Path to the restart files.
    separate (bool): Whether to create a separate run directory for each simulation.

    Returns:
    str: Path to the run directory.
    """

    # Create a run directory
    run_directory_name = 'run' if not separate else f'run_{new_name}'
    run_directory = os.path.join(work_dir, run_directory_name)
    results_directory = os.path.join(work_dir, 'results')
    os.makedirs(run_directory, exist_ok=True)
    os.makedirs(results_directory, exist_ok=True)

    # Copy necessary files from the template directory
    copy_template_files(executable_name, new_name, Path(template_dir), Path(run_directory))

    # Copy the restart file if it exists
    if not restart_files is None:
        restart_files = glob.glob(restart_files)
        if restart_files:
            for file in restart_files:
                dest_file = os.path.join(results_directory, os.path.basename(file))
                if not os.path.exists(dest_file):
                    shutil.copy(file, dest_file)

    return run_directory

def parse_to_dict(file_path: str, reset: Optional[bool] = False) -> dict[str, Union[str, int, float]]:
    """
    Parse a file to a dictionary.

    Parameters:
    file_path (str): Path to the file to parse.

    Returns:
    dict: Parsed dictionary.
    """

    config_dict: dict[str, Union[str, int, float]] = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            # Remove comments and whitespace
            code = line.split('#',1)[0].strip()
            if not code and "=" not in code and ":" not in code:
                continue
            symbol = "=" if "=" in code else ":"
            key, value = map(str.strip, code.split(symbol, 1))
            config_dict[key] = infer_type(value, reset)

    return config_dict

def infer_type(value:str, reset: Optional[bool] = False) -> Union[str, int, float]:
    """
    Infer the type of a value from a string.

    Parameters:
    value (str): Value to infer type from.

    Returns:
    Union[str, int, float]: Inferred type value.
    """
    # remove leading and trailing whitespace
    v = value.strip()

    if v.lower() in ('.true.', 'true'):
        if reset:
            return False
        return True
    if v.lower() in ('.false.', 'false'):
        return False
    if re.fullmatch(r'[+-]?\d+', v):
        return int(v)
    if re.fullmatch(r'[+-]?\d*\.?\d*[eE][+-]?\d+', v):
        return float(v)
    if re.fullmatch(r'[+-]?\d*\.\d*', v) and '.' in v:
        return float(v)

    return v.strip('"').strip("'")

def adapt_dictionary(config_dict: dict[str, Union[str, int, float]],
                     parameter: Union[list[str], str],
                     factor: float,
                     new_value: Union[list[Union[int, float]], Union[int, float]] = None) -> dict[str, Union[str, int, float]]:

    """
    Adapt the configuration dictionary based on the parameters and relative change.

    Parameters:
    config_dict (dict): Configuration dictionary to adapt.
    parameter (str or list): Parameter(s) to adapt.
    value (Union[int, float]): New value for the parameter.

    Returns:
    dict: Adapted configuration dictionary.
    """
    if not isinstance(parameter, list):
        parameter = [parameter]
    if not isinstance(new_value, list):
        if new_value is None:
            new_value = [None]*len(parameter)
        else:
            new_value = [new_value]

    if new_value is not None:
        assert len(parameter) == len(new_value), "Length of parameter and new_value must be the same"

    for param, new_val in zip(parameter, new_value):
        original_value = config_dict[param]
        if isinstance(original_value, (int, float)):
            if new_val is None:
                config_dict[param] = factor*original_value
            else:
                config_dict[param] = new_val

        elif isinstance(original_value, bool):
            config_dict[param] = new_val
        elif isinstance(original_value, str):
            config_dict[param] = new_val

    return config_dict

def create_new_parameter_file(config_dict: dict[str, Union[str, int, float]],
                              parameter_file_name: str) -> str:

    """
    Create a new parameter file based on the configuration dictionary.

    Parameters:
    config_dict (dict): Configuration dictionary.
    executable_name (str): Name of the executable.
    parameter_suffix (str): Suffix for the parameter file.

    Returns:
    str: Path to the new parameter file.
    """
    with open(parameter_file_name, 'w', encoding='utf-8') as file:
        for key, value in config_dict.items():
            if isinstance(value, bool):
                value_str = '.true.' if value else '.false.'
            elif isinstance(value, (int, float)):
                value_str = str(value)
            else:
                value_str = f'{value}'
            file.write(f"{key} = {value_str}\n")

    return parameter_file_name
