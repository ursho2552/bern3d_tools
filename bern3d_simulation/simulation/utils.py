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
    new_name (str): New name for the simulation.

    Returns:
    str: Path to the new simulation directory.
    """
    # Define the new simulation path
    new_simulation_path = Path(work_directory) / f"run_{new_name}"

    # Step 1: Copy the template directory
    copy_template_directory(bern3d_template_path, new_simulation_path)

    # Step 2: Create the results directory
    create_results_directory(work_directory)

    # Step 3: Replace placeholders in specific files
    replace_placeholders_in_files(new_simulation_path, bern3d_template_name, new_name)

    # Step 4: Rename files that start with the old name
    rename_files(new_simulation_path, bern3d_template_name, new_name)

    return new_simulation_path

def copy_template_directory(template_path: str, destination_path: Path) -> None:
    """
    Copy the template directory to the destination path.

    Parameters:
    template_path (str): Path to the template directory.
    destination_path (Path): Path to the destination directory.

    Returns:
    None
    """
    shutil.copytree(template_path, destination_path, dirs_exist_ok=True)


def create_results_directory(work_directory: str) -> None:
    """
    Create a results directory in the work directory.

    Parameters:
    work_directory (str): Path to the work directory.

    Returns:
    None
    """
    results_dir = Path(work_directory) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)


def replace_placeholders_in_files(directory: Path, old_name: str, new_name: str) -> None:
    """
    Replace placeholders in specific files within the directory.

    Parameters:
    directory (Path): Path to the directory containing the files.
    old_name (str): Placeholder to replace.
    new_name (str): New value to replace the placeholder with.

    Returns:
    None
    """
    files_to_edit = ["parallel.sh", "parallel_investor.sh", f"{old_name}.main.parameter"]

    for file_name in files_to_edit:
        file_path = directory / file_name
        if file_path.exists():
            with file_path.open('r', encoding='utf-8') as file:
                content = file.read()
            content = content.replace(old_name, new_name)
            with file_path.open('w', encoding='utf-8') as file:
                file.write(content)
        else:
            logging.warning("%s not found!", file_name)


def rename_files(directory: Path, old_name: str, new_name: str) -> None:
    """
    Rename files in the directory that start with the old name.

    Parameters:
    directory (Path): Path to the directory containing the files.
    old_name (str): Old name to replace.
    new_name (str): New name to use.

    Returns:
    None
    """
    for file in directory.glob(f"{old_name}*"):
        new_file_name = file.name.replace(old_name, new_name)
        file.rename(directory / new_file_name)
        logging.info("Renamed: %s -> %s", file, directory / new_file_name)


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

    result = subprocess.run(command, check=True, capture_output=True, text=True)
    job_id = result.stdout.strip().split()[-1]

    return job_id
