#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the utils script for the sensitivity analysis module.
"""

import os
import glob
from dataclasses import dataclass

@dataclass
class ConfigParameters:
    """
    Configuration parameters for the sensitivity analysis.
    """
    # Bern3D files
    bern3d_template: str
    bern3d_executable_name: str
    bern3d_parameter_file: str
    bern3d_restart_files: str

    # Sensitivity analysis parameters
    parameter_list: dict[str, float | None]
    relative_change: float
    target_field: dict[str, str]

    # Work directory and scripts to use
    work_directory: str
    bern3d_run_script: str
    evaluation_script: str
    main_script_path: str
    time_bern3d: str
    time_evaluation: str

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
    assert os.path.exists(config.bern3d_run_script), "BERN3D run script does not exist."
    assert os.path.exists(config.evaluation_script), "Evaluation script does not exist."

    if config.bern3d_restart_files:
        restart_files = glob.glob(config.bern3d_restart_files)
        assert restart_files, f"No restart files found matching pattern: {config.bern3d_restart_files}"
    assert config.relative_change > 0, "Relative change must be greater than zero."

    assert config.time_bern3d.count(":") == 2, "Time format must be HH:MM:SS."
    assert int(config.time_bern3d.split(":")[0]) < 96, "Time in hours must be less than 96."
    assert config.time_evaluation.count(":") == 2, "Time format must be HH:MM:SS."
    assert int(config.time_evaluation.split(":")[0]) < 96, "Time in hours must be less than 96."
    # Check if the work directory exists, if not create it
    if not os.path.exists(config.work_directory):
        os.makedirs(config.work_directory)

    return config
