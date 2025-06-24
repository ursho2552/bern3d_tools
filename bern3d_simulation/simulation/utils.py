#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model with possible restart.
"""
import logging
import shutil
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
