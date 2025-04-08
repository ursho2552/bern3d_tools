#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model with possible restart.
"""
import logging
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Type, Optional, TypeVar

import yaml

Config = TypeVar('Config')

@dataclass
class JobConfig:
    """
    This dataclass contains the configuration parameters for the job submission.
    """
    # Path to the script template
    bern3d_template: str
    bern3d_executable_name: str

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

def read_config_file(config_file: str,
                     config_class: Type[Config] = JobConfig) -> Config:
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

    return config

def create_simulation_run_directory(bern3d_template_path: str, bern3d_template_name: str,
                                    work_directory: str, new_name: str) -> str:
    """
    Create a spinup run directory and copy the template files to it.

    Parameters:
    bern3d_template_path (str): Path to the template files.
    bern3d_template_name (str): Name of the template files.
    work_directory (str): Path to the work directory.

    Returns:
    str: Path to the new simulation directory.
    """

    # copy the whole directory
    new_simulation_path = Path(work_directory) / f"run_{new_name}"
    shutil.copytree(bern3d_template_path, new_simulation_path, dirs_exist_ok=True)

    # In the parent directory, create an empty directory called results
    results_dir = Path(work_directory) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Replace old_name with new_name in specific files
    files_to_edit = ["parallel.sh",
                     "parallel_investor.sh",
                     f"{bern3d_template_name}.main.parameter"]

    for file_name in files_to_edit:
        file_path = new_simulation_path / file_name
        if file_path.exists():
            with file_path.open('r', encoding='utf-8') as file:
                content = file.read()
            content = content.replace(bern3d_template_name, new_name)
            with file_path.open('w', encoding='utf-8') as file:
                file.write(content)
        else:
            logging.warning("%s not found!", file_name)

    # Rename files that start with old_name
    for file in new_simulation_path.glob(f"{bern3d_template_name}*"):
        new_file_name = file.name.replace(bern3d_template_name, new_name)
        file.rename(new_simulation_path / new_file_name)
        logging.info("Renamed: %s -> %s", file, new_simulation_path / new_file_name)

    return new_simulation_path

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

def submit_job(script_template: str, executable_name: str, executable_path: str, time: str,
               dependency: Optional[str] = None,
               command_line_arg: Optional[list[str]] = None,
               dependency_type: Optional[str] = 'afterok') -> str:
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

        command.append(f"--dependency={dependency_type}:{dependency_ids}")

    command.append(script_template)

    if (command_line_arg is not None) and (len(command_line_arg) > 0):
        for arg in command_line_arg:
            command.append(arg)

    print(command)
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]

    return job_id
