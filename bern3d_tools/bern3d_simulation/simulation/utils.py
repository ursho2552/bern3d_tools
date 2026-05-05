#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model with possible restart.
"""
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, TypeVar

Config = TypeVar('Config')

@dataclass
class JobConfig:
    """
    This dataclass contains the configuration parameters for the job submission.
    """
    # Path to the script template
    bern3d_template: str
    bern3d_executable_name: str
    bern3d_restart_files: str

    # Path to the work directory
    work_directory: str
    simulation_name: str

    # Path to the executables
    bern3d_submit_script: str
    python_script: str
    main_script: str

    time_bern3d: str
    time_python: str

    config_file: str

def check_configuration(config_dataclass: JobConfig) -> JobConfig:
    """
    Check the configuration file for errors and raise exceptions if any are found.
    This function checks if the paths exist, if the work directory exists,
    and if the spinup phases are valid.

    Parameters:
    config_dataclass (JobConfig): The configuration dataclass to check.

    Returns:
    JobConfig: The configuration dataclass if no errors are found.
    """
    # Check if the configuration file is valid
    assert '.yaml' in config_dataclass.config_file.lower(), "The configuration file should be a '.yaml' file"

    # Check if the template path exists
    assert Path(config_dataclass.bern3d_template).exists(), f"Template path {config_dataclass.bern3d_template} does not exist."

    # Check if the work directory exists
    if not Path(config_dataclass.work_directory).exists():
        logging.info(f"Work directory {config_dataclass.work_directory} does not exist. Creating it.")
        Path(config_dataclass.work_directory).mkdir(parents=True, exist_ok=True)

    # Check if the executable name is valid
    assert config_dataclass.bern3d_executable_name, "Executable name cannot be empty."

    return config_dataclass

def check_simulation_status(run_path: str, executable_name: str,
                            success_string: Optional[str] = "SIMULATION COMPLETE") -> bool:
    """
    This functions checks if the simulation finished successfully. This is done by checking the
    output file of the Bern3D executable. If the simulation finished successfully, the output file
    will contain the string given in success_string.

    Parameters:
    run_path (str): Path to the work directory where the results directory in contained
    executable_name (str): Name of the Bern3D executable used, which is used to read in the output
                            file (f"{executable_name}.out")
    success_string (str): String to check in the output file. Default is "SIMULATION COMPLETE".

    Returns:
    bool: True if the simulation finished successfully, False otherwise.
    """

    finished = False

    output_file = f"{run_path}/{executable_name}.out"
    # Check if the output file exists
    assert Path(output_file).exists(), f"Output file {output_file} does not exist."

    # If passed, check log file (not sure if try except would be better) -> better to be strict
    # and keep the assert to throw the error
    with open(output_file, encoding='utf-8') as file:
        if success_string in file.read():
            finished = True

    return finished
