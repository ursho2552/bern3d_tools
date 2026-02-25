#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the utils script for the sensitivity analysis module.
"""

import sys
import os
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.append(repo_root)

import glob
from dataclasses import dataclass

import bern3d_tools.shared.utils as shared_utils

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
    parameter_list: dict[str, float | list[float] | None]
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

    list_parameter_files = config.bern3d_parameter_file.split(",")
    param_files = []
    for file in list_parameter_files:
        full_path = f"{config.bern3d_template}/{config.bern3d_executable_name}{file}"
        assert os.path.exists(full_path), f"BERN3D parameter file does not exist: {full_path}"
        param_files.append(full_path)

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

    # check that all the parameters in the parameter list are present in the parameter file
    # there might be a list of param files
    for parameter in config.parameter_list.keys():
        missing_in_files = 0
        for file in param_files:
            param_file_dict, _ = shared_utils.parse_to_dict(file_path=file)
            if parameter is not None and parameter not in param_file_dict:
                missing_in_files =+ 1
        if missing_in_files == len(param_files):
            raise ValueError(f"Parameter '{parameter}' not found in the parameter file. Please check the parameter name and ensure it exists in the template parameter file.")

    return config
