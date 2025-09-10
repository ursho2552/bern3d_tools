#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model spinup depending on the user configuration
"""

from typing import TypeVar
from dataclasses import dataclass
from pathlib import Path

ConfigFile = TypeVar('ConfigFile')

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

    # Paths to the sbatch scripts for each phase
    sbatch_script: dict[str, str]

    # Time to run the script
    time: str

    # Spinup phases to run
    # 1: spinup phase 1
    # 2: spinup phase 1 & 2
    # 3: spinup phase 1, 2 & 3
    spinup_phases: int
    current_phase: int

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

    # Check if the paths exist
    paths_to_check = [config_dataclass.bern3d_template]
    sbatch_paths = list(config_dataclass.sbatch_script.values())
    paths_to_check.extend(sbatch_paths)
    for path in paths_to_check:
        if not Path(path).exists():
            raise FileNotFoundError(f"Path {path} does not exist.")

    # Check if the work directory exists
    if not Path(config_dataclass.work_directory).exists():
        # create it if it does not exist
        Path(config_dataclass.work_directory).mkdir(parents=True, exist_ok=True)

    assert config_dataclass.spinup_phases in [1, 2, 3], "Spinup phases must be either 1, 2 or 3"
    assert config_dataclass.current_phase <= config_dataclass.spinup_phases, "Current phase must be either 1, 2 or 3 and less than or equal to spinup phases"
    assert config_dataclass.current_phase > 0, "Current phase must be either 1, 2 or 3 and greater than 0"

    return config_dataclass
