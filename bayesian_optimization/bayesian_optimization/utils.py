#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used in the Bayesian optimization module.
"""
import os
import glob
import shutil
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Type, Optional, Union

import yaml
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
    isotope (str): Isotope type ("Pad" or "Thd").
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

    bern3d_script_time: str
    postprocessing_script_time: str
    optimizer_script_time: str

    # Path to output directory of bern3d
    simulation_name_bern3d: str
    output_type_bern3d: str
    output_timescale_bern3d: str
    work_directory: str
    output_files_bern3d: str
    bern3d_f90: bool
    template_name_bern3d: str
    bern3d_template: str
    initialization_file: str

    # Path where you want to store the output of the optimizer
    validation_data_path: str
    output_dir_optimizer: str

    # The number of iterations to run the Bayesian optimization algorithm
    max_iterations: int

    parameter_mapping: dict[str, float]
    parameter_bounds: dict[str, tuple[float, float]]

    # Path to file with parameters to be optimized
    parameter_file: str

    initialization_type: str
    isotope: str
    n_initialization: int
    surrogate_type: str
    acquisition_type: str
    batchsize: int
    acquisitition_optimizer: str
    job_number: int


def read_config_file(config_file: str,
                      config_class: Type[ConfigParameters] = ConfigParameters) -> ConfigParameters:
    """
    This function reads a configuration file, and fills in the attributes of the dataclass with
    the respective entries in the configuratio file

    Parameters:
    config_file (str): Path to the configuration file
    config_class (Type[ConfigParameters]): The dataclass to be filled with the configuration entries

    Returns:
    ConfigParameters: The dataclass with the configuration entries filled in
    """
    assert '.yaml' in config_file.lower(), "The configuration file should be a '.yaml' file"

    with open(config_file, encoding='utf-8') as file:
        config_list = yaml.load(file, Loader=yaml.FullLoader)

    config = config_class(**config_list)

    # Check if the paths exist
    assert os.path.exists(config.bern3d_script), f"Path {config.bern3d_script} does not exist"
    assert os.path.exists(config.postprocessing_script), f"Path {config.postprocessing_script} does not exist"
    assert os.path.exists(config.optimizer_script), f"Path {config.optimizer_script} does not exist"
    assert os.path.exists(config.bern3d_template), f"Path {config.bern3d_template} does not exist"
    assert config.initialization_type in ["lhs", "random", "sobol", "halton", "hammersly", "lhs", "grid", "simulation"], "Initialization type not found"

    assert config.output_tpye_bern3d in ["timeseries", "full"], "Output type not found"
    assert config.output_timescale_bern3d in ["inst", "ave"], "Output timescale not found"

    assert "simulation_name_bern3d" in config.parameter_file, "simulation_name_bern3d not found in parameter file"
    if os.path.exists(config.output_dir_optimizer) is False:
        os.makedirs(config.output_dir_optimizer)

    if os.path.exists(config.output_files_bern3d) is False:
        os.makedirs(config.output_files_bern3d)

    # check if the time is in the correct format
    assert config.bern3d_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"
    assert config.postprocessing_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"
    assert config.optimizer_script_time.count(":") == 2, "Time format is incorrect (hh:mm:ss)"

    # Check that hours in the time are less then 96
    assert int(config.bern3d_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"
    assert int(config.postprocessing_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"
    assert int(config.optimizer_script_time.split(":")[0]) < 96, "Hours in the time are more than 96"

    return config


def access_file(model_output_files: str, simulation_name: Union[str, list[str]], output_type: str,
                output_timescale: str) -> dict[str, xr.Dataset]:
    """
    Opens the corresponding file based on the provided parameters.

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
    all_files = glob.glob(f"{model_output_files}/*", recursive=True)
    filtered_files = []
    for sim in simulation_name:
        for file in all_files:
            if sim in file and output_type in file and output_timescale in file:
                filtered_files.append(file)

    # Check if the path is empty
    if not filtered_files:
        raise FileNotFoundError(f"No files found for {model_output_files}")

    if len(filtered_files) == 1:
        single_file = filtered_files[0]
        return {single_file: xr.open_dataset(single_file, decode_times=False)}

    # Return a dictionary of all filtered paths
    return {
        file: xr.open_dataset(file, decode_times=False)
        for file in filtered_files
    }

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
            lines[line_number] = f"{param}                               {value}\n"

    with open(bgc_parameter_file, 'w', encoding='utf-8') as file:
        file.writelines(lines)

    logging.info("Updated parameter file")

def create_new_simulation(new_name: str, old_name: str,
                          template_path: str, work_directory: str,
                          flag: Optional[bool] = False,
                          bern3d_f90: Optional[bool] = False,
                          initialization_file: Optional[str] = None,
                          initialization_destination: Optional[str] = None) -> str:
    """
    Copies and renames parameter files based on the provided input and output names.

    Parameters:
    new_name (str): New name for the simulation.
    old_name (str): Old name of the simulation in the template.
    template_path (str): Path to the template directory with Bern3d model.
    work_directory (str): Path to the work directory.
    flag (bool): Flag to indicate if the parameter files should be removed.
    bern3d_f90 (bool): Flag to indicate if the F90 version of Bern3D is used (True) or the Bern3D-V3 (False).
    initialization_file (str): Path to the initialization file.
    initialization_destination (str): Path to the destination for the initialization file.

    Returns:
    str: Path to the new simulation
    """
    if bern3d_f90:

        # copy the whole directory
        new_simulation_path = Path(work_directory) / f"run_{new_name}"
        shutil.copytree(template_path, new_simulation_path, dirs_exist_ok=True)

        # Replace old_name with new_name in specific files
        files_to_edit = ["parallel.sh", "parallel_investor.sh", f"{old_name}.main.parameter"]
        for file_name in files_to_edit:
            file_path = new_simulation_path / file_name
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as file:
                    content = file.read()
                content = content.replace(old_name, new_name)
                with file_path.open('w', encoding='utf-8') as file:
                    file.write(content)
            else:
                logging.warning("%s not found!", file_name)

        # Rename files that start with old_name
        for file in new_simulation_path.glob(f"{old_name}*"):
            new_file_name = file.name.replace(old_name, new_name)
            file.rename(new_simulation_path / new_file_name)
            logging.info("Renamed: %s -> %s", file, new_simulation_path / new_file_name)

    else:

        # copy the whole directory
        new_simulation_path = Path(work_directory) / f"run_{new_name}"
        shutil.copytree(template_path, new_simulation_path, dirs_exist_ok=True)

        if len(new_name) == 10 and len(old_name) == 10:

            for x in new_simulation_path.glob(f"{old_name}*"):
                parts = x.name.split('.')
                if len(parts) >= 3:
                    shutil.move(x, f"{new_simulation_path}/{new_name}.{parts[1]}.{parts[2]}")
            try:
                (new_simulation_path / f"{new_name}..").unlink()
                (new_simulation_path / f"{new_name}.out.").unlink()
            except FileNotFoundError:
                pass
        else:
            raise ValueError("ERROR: both names have to be 10 characters long")

        if flag:
            for suffix in ["forcing.parameter", "sed.parameter", "fw.parameter", "lpj.parameter", "lpj.filenames", "pisces.parameter"]:
                try:
                    os.remove(f"{new_simulation_path}/{new_name}.{suffix}")
                except FileNotFoundError:
                    pass

        # make a copy of the executable
        shutil.copy(f"{template_path}/{old_name}", f"{new_simulation_path}/{new_name}")
        # remove the files with the old name
        for file in new_simulation_path.glob(f"{old_name}*"):
            os.remove(file)

    if initialization_file is not None and initialization_destination is not None:
        # if initialization file does not exist in destination, copy it
        file_name = Path(initialization_file).name
        if not os.path.exists(f"{initialization_destination}/{file_name}"):
            shutil.copy(initialization_file, initialization_destination)

    # for some strange reason, Bern3d-v3 needs the input directory...
    if not os.path.exists(f"{work_directory}/input"):
        input_directory_path = Path(template_path).parent / "input"
        shutil.copytree(input_directory_path, f"{work_directory}/input", dirs_exist_ok=True)

    return new_simulation_path


def submit_job(script_template: str, executable_name: str, executable_path: str, time: str,
               dependency: Optional[str] = None,
               command_line_arg: Optional[list[str]] = None) -> str:
    """
    Submit a job using sbatch with optional dependency and iteration parameters.

    Parameters:
    script_template (str): Path to the script template.
    executable_name (str): Name of the executable.
    executable_path (str): Path to the executable.
    time (str): Time to run the script.
    dependency (str): Dependency job id.
    command_line_arg (list): List of command line arguments.

    Returns:
    str: JobID of the submitted job.
    """
    # define command
    command = ["sbatch"]

    command.append(f"--job-name={executable_name}")
    command.append(f"--time={time}")
    command.append(f"--chdir={executable_path}")

    # check if dependency is provided
    if dependency:

        if len(dependency) == 1:
            dependency_ids = dependency[0]
        else:
            dependency_ids = ":".join(dependency)

        command.append(f"--dependency=afterok:{dependency_ids}")

    command.append(script_template)

    if (command_line_arg is not None) and (len(command_line_arg) > 0):
        for arg in command_line_arg:
            command.append(arg)

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]

    return job_id
