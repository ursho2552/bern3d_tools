#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the utils script for the sensitivity analysis module.
"""

import os
import glob
import shutil
import logging
from pathlib import Path
import re
from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class ConfigParameters:
    """
    Configuration parameters for the sensitivity analysis.
    """
    bern3d_template: str
    bern3d_executable_name: str
    bern3d_parameter_file: str
    bern3d_restart_files: str
    parameter_list: str
    relative_change: float
    work_directory: str
    sensitivity_script: str
    time: str

def check_configuration(config: ConfigParameters) -> ConfigParameters:
    """
    Check and validate the configuration parameters.

    Parameters:
    config (ConfigParameters): Configuration parameters to validate.

    Returns:
    ConfigParameters: Validated configuration parameters.
    """
    assert os.path.exists(config.bern3d_template), "BERN3D template directory does not exist."
    assert os.path.exists(f"{config.bern3d_template}/{config.bern3d_executable_name}"), "BERN3D executable does not exist."
    param_file = f"{config.bern3d_template}/{config.bern3d_executable_name}{config.bern3d_parameter_file}"
    assert os.path.exists(param_file), "BERN3D parameter file does not exist."
    if config.sensitivity_script:
        restart_files = glob.glob(config.bern3d_restart_files)
        assert restart_files, f"No restart files found matching pattern: {config.bern3d_restart_files}"
    assert config.relative_change > 0, "Relative change must be greater than zero."

    assert config.time.count(":") == 2, "Time format must be HH:MM:SS."
    assert int(config.time.split(":")[0]) < 96, "Time in hours must be less than 96."
    # Check if the work directory exists, if not create it
    if not os.path.exists(config.work_directory):
        os.makedirs(config.work_directory)

    return config

def infer_type(value:str) -> Union[str, int, float]:
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

def parse_to_dict(file_path: str) -> dict[str, Union[str, int, float]]:
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
            code = line.split('#',1)[0].strip()  # Remove comments
            if not code or "=" not in code:
                continue
            key, value = map(str.strip, code.split('=', 1))
            config_dict[key] = infer_type(value)

    return config_dict

def adapt_dictionary(config_dict: dict[str, Union[str, int, float]],
                     parameter: str,
                     factor: float) -> dict[str, Union[str, int, float]]:

    """
    Adapt the configuration dictionary based on the parameters and relative change.

    Parameters:
    config_dict (dict): Configuration dictionary to adapt.
    parameter (str): name of parameter to change.
    value (Union[int, float]): New value for the parameter.

    Returns:
    dict: Adapted configuration dictionary.
    """

    original_value = config_dict[parameter]
    if isinstance(original_value, (int, float)):
        if original_value == 0:
            raise ValueError(f"Parameter '{parameter}' cannot be zero for relative change.")

        config_dict[parameter] = factor*original_value

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

def copy_template_files(exec_name: str, new_name: str,
                        template_dir: Path, work_dir: Path) -> None:
    """
    Copy only the necessary model files for a specific executable.

    Parameters:
    exec_name (str): Name of the executable.
    template_dir (Path): Path to the template directory.
    work_dir (Path): Path to the working directory.

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

        # Determine destination filename
        if name.startswith(exec_name):
            # rename file itself
            new_filename = name.replace(exec_name, new_name, 1)
        else:
            new_filename = name

        # Copy if shared or specific to exec_name
        if name.startswith(exec_name) or not any(name.startswith(prefix) for prefix in exec_names):
            dest = work_dir / new_filename
            shutil.copy2(file, dest)
            copied_files.append(dest)
            print(f"Copied: {name} -> {new_filename}")

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
            print(f"Replaced '{exec_name}' with '{new_name}' in: {file_path.name}")

def setup_run_directory(template_dir: str, executable_name: str,
                        new_name: str, work_dir: str,
                        restart_files: str) -> str:
    """
    Set up the run directory for the sensitivity analysis.

    Parameters:
    template_dir (str): Path to the template directory.
    executable_name (str): Name of the executable.
    new_name (str): New name for the executable.
    work_dir (str): Path to the working directory.
    restart_files (str): Path to the restart files.

    Returns:
    str: Path to the run directory.
    """
    # Create a run directory
    run_directory = os.path.join(work_dir, "run")
    results_directory = os.path.join(work_dir, "results")
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
                    shutil.copy2(file, results_directory)

    return run_directory


def update_parameter_file(parameter_file: str, parameter: str, value: Union[float, int]) -> None:
    """
    Update the parameter file with the new parameter value.

    Parameters:
    parameter_file (str): Path to the parameter file.
    parameter (str): Parameter to update.
    value (Union[float, int]): New value for the parameter.

    Returns:
    None
    """
    with open(parameter_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    with open(parameter_file, 'w') as file:
        for line in lines:
            if line.startswith(parameter):
                line = f"{parameter} = {value}\n"
            file.write(line)
