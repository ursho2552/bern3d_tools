#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model spinup depending on the user configuration
"""
import re
import logging
import shutil
import subprocess
from typing import Type, Optional, TypeVar, Any
from dataclasses import dataclass, make_dataclass, field
from pathlib import Path

import yaml

ConfigFile = TypeVar('ConfigFile')

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
    # Path of the sbatch script
    sbatch_script_phase1: str
    sbatch_script_phase2: str
    sbatch_script_phase3: str
    # Time to run the script
    time: str

    # Spinup phases to run
    # 1: spinup phase 1
    # 2: spinup phase 1 & 2
    # 3: spinup phase 1, 2 & 3
    spinup_phases: int
    current_phase: int

def infer_type(value: str) -> Any:
    """
    Infer the type of a value based on its string representation.
    Boolean values are all converted to False.
    Integer values are set to 0.
    Floating point values are set to 0.0.
    String values are returned as is.

    Parameters:
    value (str): The string representation of the value.

    Returns:
    Any: The inferred value, which can be a string, int, float, or bool.
    """
    v = value.strip()

    if v.lower() in ('.true.', 'true'):
        return False
    if v.lower() in ('.false.', 'false'):
        return False
    if re.fullmatch(r'[+-]?\d+', v):
        return 0
    if re.fullmatch(r'[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?', v):
        return 0.0

    return v.strip('"').strip("'")

def parse_to_dict(path: str) -> dict[str, Any]:
    """
    Parse a configuration file and return a dictionary of key-value pairs.
    This function reads a configuration file line by line, ignoring comments and empty lines.
    It splits each line into a key and a value, inferring the type of the value.
    The function supports boolean, integer, and floating point values.

    Parameters:
    path (str): Path to the configuration file.

    Returns:
    dict: A dictionary containing the key-value pairs from the configuration file.
    """

    cfg: dict[str, Any] = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            code = line.split('#',1)[0].strip()
            if not code or '=' not in code:
                continue
            key, val = map(str.strip, code.split('=',1))
            cfg[key] = infer_type(val)
    return cfg

def adapt_dict(original: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Adapt the original dictionary with the values from the override dictionary.
    This function will only override the values in the original dictionary
    if the keys exist in both dictionaries.

    Parameters:
    original (dict): The original dictionary to be adapted.
    override (dict): The dictionary with values to override the original.

    Returns:
    dict: The adapted dictionary with the overridden values.
    """

    for key, value in override.items():
        if key in original:
            original[key] = value

    return original

def get_main_config_fields(config_file: str, override_dict: dict[str, Any],
                           phase: int) -> ConfigFile:
    """
    This function reads the configuration file and adapts it to the spinup phase.
    It uses the override dictionary to set the values for the spinup phase.
    The function returns a dataclass with the configuration parameters.
    The dataclass is created dynamically based on the keys and values in the configuration file.

    Parameters:
    config_file (str): Path to the configuration file.
    override_dict (dict): The dictionary with values to override the original.
    phase (int): The current spinup phase.

    Returns:
    ConfigMainParameters: The dataclass with the configuration parameters.
    """

    dictionary_fields = parse_to_dict(config_file)

    for p in range(1, phase + 1):
        dictionary_fields = adapt_dict(dictionary_fields, override_dict[f"phase_{p}"])
    fields: list[tuple[str, type, Any]] = []
    for key, value in dictionary_fields.items():
        fields.append((key, type(value), field(default=value)))

    parsed_config = make_dataclass("ConfigMainParameters", fields)

    return parsed_config()


def read_config_file(config_file: str, config_class: Type[ConfigFile]) -> ConfigFile:
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

    # If the config file is of type JobConfig, check that the paths exist
    if isinstance(config, JobConfig):
        # Check if the paths exist
        paths_to_check = [config.bern3d_template, config.sbatch_script_phase1,
                          config.sbatch_script_phase2, config.sbatch_script_phase3]

        for path in paths_to_check:
            if not Path(path).exists():
                raise FileNotFoundError(f"Path {path} does not exist.")

        # Check if the work directory exists
        if not Path(config.work_directory).exists():
            # create it if it does not exist
            Path(config.work_directory).mkdir(parents=True, exist_ok=True)


        assert config.spinup_phases in [1, 2, 3], "Spinup phases must be either 1, 2 or 3"
        assert config.current_phase <= config.spinup_phases, "Current phase must be either 1, 2 or 3 and less than or equal to spinup phases"
        assert config.current_phase > 0, "Current phase must be either 1, 2 or 3 and greater than 0"

    return config

def create_spinup_run_directory(bern3d_template_path: str, bern3d_executable_path: str,
                                work_directory: str, phase: int,
                                replicate: int = None ) -> str:
    """
    Create a spinup run directory and copy the template files to it.

    Parameters:
    bern3d_template_path (str): Path to the template files.
    bern3d_executable_path (str): Path to the Bern3D executable.
    work_directory (str): Path to the work directory.

    Returns:
    str: Path to the new simulation directory.
    """

    # copy the whole directory
    if replicate is not None:
        new_name = f"Spinup_{replicate}"
    else:
        new_name = "Spinup"

    new_name_executable = f"Spinup{phase}"

    # Create a new directory for the simulation and copy the template files to it
    new_simulation_path = Path(work_directory) / f"run_{new_name}"
    shutil.copytree(bern3d_template_path, new_simulation_path, dirs_exist_ok=True)

    # Extract the name of the template executable
    bern3d_template_name = Path(bern3d_executable_path).name
    # copy the executable to the new directory
    shutil.copy(bern3d_executable_path, new_simulation_path / new_name_executable)

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
            content = content.replace(bern3d_template_name, new_name_executable)
            with file_path.open('w', encoding='utf-8') as file:
                file.write(content)
        else:
            logging.warning("%s not found!", file_name)

    # Rename files that start with old_name
    for file in new_simulation_path.glob(f"{bern3d_template_name}*"):
        new_file_name = file.name.replace(bern3d_template_name, new_name_executable)
        file.rename(new_simulation_path / new_file_name)
        logging.info("Renamed: %s -> %s", file, new_simulation_path / new_file_name)

    return new_simulation_path


def save_config_as_assignment(config: ConfigFile, config_file_path: str) -> None:

    """
    Save the configuration as a Python assignment file.

    Parameters:
    config (ConfigMainParameters): The configuration object to save.
    config_file_path (str): The path to the output file.
    """
    values_to_convert = ['npstp_years', 'iwstp_years', 'itstp_years', 't00']
    # Remove config_file_path if it exists already
    if Path(config_file_path).exists():
        Path(config_file_path).unlink()

    with open(config_file_path, 'w', encoding='utf-8') as f:
        for key, value in config.__dict__.items():

            # Convert boolean to string with .true. or .false.
            if isinstance(value, bool):
                value = ".true." if value else ".false."
            # Convert numpy int to to string with .0
            if key in values_to_convert:
                value = f"{value}.0"

            f.write(f"{key} = {value}\n")


def submit_job(script_template: str, executable_name: str, executable_path: str, time: str,
               header_command: Optional[str] = None,
               dependency: Optional[str] = None,
               dependency_type: Optional[str] = 'afterok',
               command_line_arg: Optional[list[str]] = None) -> str:
    """
    Submit a job using sbatch with optional dependency and iteration parameters.

    Parameters:
    script_template (str): Path to the script template.
    executable_name (str): Name of the executable.
    executable_path (str): Path to the executable.
    time (str): Time to run the script.
    header_command (str): Header command to be added to the sbatch script.
    dependency (str): Dependency job id.
    dependency_type (str): Type of dependency (afterok, afterany, other slurm option).
    command_line_arg (list): List of command line arguments.

    Returns:
    str: JobID of the submitted job.
    """
    # define command
    command = ["sbatch"]

    command.append(f"--job-name={executable_name}")
    command.append(f"--time={time}")
    command.append(f"--chdir={executable_path}")

    # check if header command is provided
    if header_command:
        command.append(header_command)

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
