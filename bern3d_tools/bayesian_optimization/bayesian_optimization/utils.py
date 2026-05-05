#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used in the Bayesian optimization module.
"""
import os
import glob
import logging
from dataclasses import dataclass
from typing import Optional, Union

import xarray as xr

@dataclass
class ConfigParameters:
    """
    This dataclass contains the configuration parameters for the Bayesian optimization module.

    Attributes:
    config_file_path (str): Path to the configuration file.
    bern3d_script (str): Path to the script used to run Bern3D.
    postprocessing_script (str): Path to the script used to run the postprocessing.
    optimizer_script (str): Path to the scirpt used to run the optimizer workflow.
    bern3d_script_time (str): Time to run the Bern3D script.
    postprocessing_script_time (str): Time to run the postprocessing script.
    optimizer_script_time (str): Time to run the optimizer script.
    simulation_name_bern3d (str): Name of the new simulation.
    output_type_bern3d (str): Type of the output to analyze.
    output_timescale_bern3d (str): Timescale of the output to analyze.
    work_directory (str): Path to the work directory.
    output_files_bern3d (str): Path where the output files are stored. Should be results directory
                               in work_directory.
    bern3d_f90 (bool): Flag to indicate if the F90 version of Bern3D is used (True) or the
                       Bern3D-V3 (False).
    template_name_bern3d (str): Name of the Bern3D executable.
    bern3d_template (str): Path to the template directory containing the Bern3D executable and
                           files.
    validation_data_path (str): Path to the validation data.
    output_dir_optimizer (str): Path to the output directory of the optimizer. Should be in the
                                work directory.
    max_iterations (int): Number of iterations to run the Bayesian optimization algorithm.
    parameter_mapping (dict): Dictionary mapping parameter names to their line numbers in the
                              parameter file (line number in file - 1).
    parameter_bounds (dict): Dictionary mapping parameter names to their bounds.
    parameter_file (str): Path to the parameter file.
    n_initialization (int): Number of initializations for the optimizer.
    tuning_target (str): Target variables of the tuning.
    surrogate_type (str): Type of surrogate model to use.
    acquisition_type (str): Type of acquisition function to use.
    batchsize (int): Batch size for the optimizer.
    acquisitition_optimizer (str): Optimizer for the acquisition function.
    job_number (int): Number of jobs to run in parallel.
    """
    config_file_path: str

    bern3d_script: str
    postprocessing_script: str
    optimizer_script: str
    python_scripts: str

    bern3d_script_time: str
    postprocessing_script_time: str
    optimizer_script_time: str

    # Path to output directory of bern3d
    simulation_name_bern3d: str
    output_type_bern3d: str
    output_timescale_bern3d: str
    wildcard_simulation: str

    work_directory: str
    output_files_bern3d: str
    bern3d_f90: bool
    bern3d_executable_name: str
    bern3d_template: str

    simulation_name_restart: str
    output_files_restart: str

    # Path where you want to store the output of the optimizer
    validation_data_path: str
    output_dir_optimizer: str

    # The number of iterations to run the Bayesian optimization algorithm
    use_reference_simulation: bool
    max_iterations: int
    max_stable_iterations: int

    target_values: dict[str, Optional[float]]

    parameter_bounds: dict[str, tuple[float, float]]
    fixed_values: dict[str, float]

    use_penalty: bool

    # Path to file with parameters to be optimized
    bern3d_parameter_file: str
    bern3d_restart_files: str

    initialization_type: str
    tuning_target: str
    n_initialization: int
    surrogate_type: str
    acquisition_type: str
    batchsize: int
    acquisitition_optimizer: str
    job_number: int

    variable_names: dict[str, dict[str, Optional[str]]]

def check_configuration(config_dataclass: ConfigParameters) -> ConfigParameters:
    """
    Check the configuration file for errors and raise exceptions if any are found.
    This function checks if the paths exist, if the work directory exists,
    and if the spinup phases are valid.

    Parameters:
    config_dataclass (ConfigParameters): The configuration dataclass to check.

    Returns:
    ConfigParameters: The configuration dataclass if no errors are found.
    """

    # Check if the paths exist
    assert os.path.exists(config_dataclass.bern3d_script), f"Path {config_dataclass.bern3d_script} does not exist"
    assert os.path.exists(config_dataclass.postprocessing_script), f"Path {config_dataclass.postprocessing_script} does not exist"
    assert os.path.exists(config_dataclass.optimizer_script), f"Path {config_dataclass.optimizer_script} does not exist"
    assert os.path.exists(config_dataclass.bern3d_template), f"Path {config_dataclass.bern3d_template} does not exist"
    assert config_dataclass.initialization_type in ["lhs", "random", "sobol", "halton", "hammersly", "lhs", "grid", "simulation"], "Initialization type not found"

    assert config_dataclass.output_type_bern3d in ["timeseries", "full"], "Output type not found"
    assert config_dataclass.output_timescale_bern3d in ["inst", "ave"], "Output timescale not found"

    # Check if the work directory exists, if not create it as well as the output directories
    if os.path.exists(config_dataclass.work_directory) is False:
        logging.info("Work directory does not exist, creating it")
        os.makedirs(config_dataclass.work_directory)

    # create the output directory for the optimizer, which should be in the work directory
    config_dataclass.output_dir_optimizer = os.path.join(config_dataclass.work_directory, "bayesian_optimization")
    config_dataclass.output_files_bern3d = os.path.join(config_dataclass.work_directory, "results")
    logging.info("Creating output directories")
    if os.path.exists(config_dataclass.output_dir_optimizer) is False:
        os.makedirs(config_dataclass.output_dir_optimizer)
    if os.path.exists(config_dataclass.output_files_bern3d) is False:
        os.makedirs(config_dataclass.output_files_bern3d)

    # check if the time is in the correct format
    assert config_dataclass.bern3d_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"
    assert config_dataclass.postprocessing_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"
    assert config_dataclass.optimizer_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"

    # Check that hours in the time are less then 96
    assert int(config_dataclass.bern3d_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"
    assert int(config_dataclass.postprocessing_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"
    assert int(config_dataclass.optimizer_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"

    # Make sure the bounds are given as tuples of floats
    bound_values = config_dataclass.parameter_bounds
    for key, values in bound_values.items():
        transformed_values = []
        for value in values:
            transformed_values.append(float(value))

        bound_values[key] = tuple(transformed_values)
    config_dataclass.parameter_bounds = bound_values

    # Handle fixed_values to ensure it's not None and filter out None values
    if config_dataclass.fixed_values is None:
        config_dataclass.fixed_values = {}
    else:
        # Filter out None values from fixed_values
        config_dataclass.fixed_values = {
            key: value for key, value in config_dataclass.fixed_values.items()
            if value is not None
        }

    # Check if the target is valid
    check_valid_target(config_dataclass.tuning_target)

    return config_dataclass

def check_valid_target(target: str) -> None:
    """
    Check if the provided target is a valid option for scoring.

    Parameters:
    target (str): The target string to check.

    Raises:
    ValueError: If the target is not a valid option.
    """
    from bayesian_optimization.scoring.targets import TargetRegistry

    available_targets = TargetRegistry.list_all_aliases()

    if target not in available_targets:
        raise ValueError(
            f"Invalid target '{target}'. Allowed options are: {available_targets}."
        )

def access_file(model_output_files: str, simulation_name: Union[str, list[str]], output_type: str,
                output_timescale: str, simulation_initialization: bool = False,
                wildcard: str = None) -> dict[str, xr.Dataset]:
    """
    Opens the corresponding file based on the provided parameters.
    Add flags for sim restart and wildcard

    Parameters:
    model_output_files (str): Path to the model output files.
    simulation_name (str or list): Name of the simulation.
    output_type (str): Type of the output to analyze.
    output_timescale (str): Timescale of the output to analyze.

    Returns:
    dict: A dictionary with the directory name as the key and the opened xarray dataset as
    the value.
    """
    if not isinstance(simulation_name, list):
        simulation_name = [simulation_name]

    # Filter files based on simulation name, output type, and output timescale
    if simulation_initialization:
        # Ensure wildcard is not None
        wildcard = "*" if wildcard is None else wildcard
        all_files = glob.glob(f"{model_output_files}/{wildcard}", recursive=True)
    else:
        all_files = glob.glob(f"{model_output_files}/*", recursive=True)

    filtered_files = []
    unsuccessful_files = []
    for sim in simulation_name:
    # find all files matching this sim, the timescale and the type
    #if fnmatch.fnmatch(file, f"*{sim}*{output_type}*{output_timescale}*"):
        matches = [
            f for f in all_files
            if sim in f and output_timescale in f and output_type in f
        ]
        if matches:
            # add every matching file to filtered_files
            filtered_files.extend(matches)
        else:
            # remember which sim had no files
            unsuccessful_files.append(f"{model_output_files}/{sim}.not_found_{output_timescale}_{output_type}.nc")
            logging.warning("Simulation %s does not match the output type or timescale", sim)

    # create dictionary with the simulation name as the key and the file as the value
    # and open the file with xarray. Add an empty xarray dataset if the file is not found
    # for the simulation name
    result_dict = {}
    for file in filtered_files:
        result_dict[file] = xr.open_dataset(file, decode_times=False)
    for file in unsuccessful_files:
        result_dict[file] = xr.Dataset()

    return result_dict

def update_parameter_file(next_parameters: list[float], bgc_parameter_file: str,
                          parameter_mapping: dict[str, float],
                          bern3d_f90: Optional[bool] = False) -> None:
    """
    Update the parameter file with the next set of parameters.

    Parameters:
    next_parameters (list): List of next parameters to update.
    bgc_parameter_file (str): Path to the parameter file.
    parameter_mapping (dict): Dictionary mapping parameter names to their line numbers in the parameter file.
    bern3d_f90 (bool): Flag to indicate if the F90 version of Bern3D is used (True) or the Bern3D-V3 (False).

    Returns:
    None
    """

    with open(bgc_parameter_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for param, value in zip(parameter_mapping.keys(), next_parameters):
        line_number = parameter_mapping[param]
        if bern3d_f90:
            lines[line_number] = f"{param} = {value}\n"
        else:
            # For Bern3D-V3, the parameter file format is different with the first 41 characters
            # for the name and the rest for the value.
            lines[line_number] = f"{param.ljust(41)}{value}\n"

    with open(bgc_parameter_file, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    logging.info("Updated parameter file")
