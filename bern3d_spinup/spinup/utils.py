#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to run the model spinup depending on the user configuration
"""
import logging
import shutil
import subprocess
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from typing import Type, Optional, TypeVar

import yaml
import numpy as np

T = TypeVar('ConfigFileType')

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
    # path to spinup configuration files
    spinup_config_files_phase1: str
    spinup_config_files_phase2: str
    spinup_config_files_phase3: str


@dataclass
class ConfigMainParameters:
    """
    This dataclass contains the configuration parameters for the Bayesian optimization module.
    """
    # timesteps/year
    ndtyear: int

    # Length of the run [years]
    runYears: int

    # Inverse output frequency for standard output [years]
    npstp_years: int

    # Inverse output frequency for full output/restart file [years]
    iwstp_years: int

    # inverse output frequency for timeseries output [years]
    itstp_years: int

    # NetCDF output precision (single or double)
    precision: str

    # time (year AD, CE) for start of run (choose -1. to take time from restart)
    # year for orbital forcing if ebm_const_insol is chosen
    # classically 1765 for pre-industrial
    t00: int

    #########################################################
    # RESTART PARAMETERS
    #########################################################
    # Filename of restart file (also for separate sediment restart files)
    lin_name: str

    # Output number of restart file. If 0, no restart file is read-in, if -1, last time step is read-in
    lin_nr: int

    #########################################################
    # RUN DESCRIPTION
    #########################################################
    # Run description (max. 200 chars, can be changed by modifying _cdf_max_strlen)
    rundesc: str

    #########################################################
    # RUN OPTIONS
    #########################################################
    ################# GENERAL #################
    # Diagnostic of convective shuffling
    diag_conv_opt: bool
    # Diagnose heat transport
    diag_heat_opt: bool

    ################ ATMOSPHERE ###############
    # T and S restoring
    atmTSres: bool
    # Initialize and run EBM module
    atm_init: bool
    # EBM control perturb
    atmCTRLpert: bool
    # EBM constant insolation
    atmConstInsol: bool

    ################ ICE-SHEETS ###############
    # Prescribed ice sheets
    ice_opt1: bool
    # If presc ice sheet, account for FW
    ice_opt2: bool
    # If presc ice sheet, account for heat
    ice_opt3: bool
    # Couple 3D CISM icesheet
    ice_opt4: bool

    ################### BGC ###################
    # Initialize and run BGC
    bgc_opt1: bool
    # BGC Spinup?
    bgc_opt2: bool
    # Dynamic particle flux module
    bgc_opt3: bool
    # Simple 4-box land model
    bgc_opt4: bool
    # Additional diagnostics: AOflux, remin, lowO2,virtflux
    bgc_opt5: bool
    # Linear gas exchange scaling with wind speed
    bgc_opt6: bool
    # Apply virtual fluxes to tracers
    bgc_opt7: bool
    # N2O tracer
    bgc_opt8: bool
    # 143Nd and 144Nd tracers
    bgc_opt9: bool
    # 231Pa and 230Th tracers
    bgc_opt10: bool
    # Explicit Pa and Th tracers
    bgc_opt11: bool
    # Cr(III) and Cr(VI) tracers
    bgc_opt12: bool
    # 9Be and 10Be tracers
    bgc_opt13: bool
    # Ocean only noble gases (N2, Ar, Kr, Xe)
    bgc_opt14: bool
    # Diagnostic Pa and Th tracers
    bgc_opt15: bool
    # Number of dye tracers
    bgc_ntr_dye: int

    ################ SEDIMENTS #################
    # Initialize and run sediment module
    sed_opt1: bool
    # Variable weathering
    sed_opt2: bool
    # Adding weathering to coastline
    sed_opt3: bool

    ############# EXPERIMENT OPT ###############
    # Enable LGM energy dissipation rate (EDR) due to sealevel change
    expLGM_EDR: bool
    # Enable LGM wind stress
    expLGM_wind: bool


def read_config_file(config_file: str, config_class: Type[T]) -> T:
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
                          config.sbatch_script_phase2, config.sbatch_script_phase3,
                          config.spinup_config_files_phase1, config.spinup_config_files_phase2,
                          config.spinup_config_files_phase3]

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

def create_spinup_run_directory(bern3d_template_path: str, bern3d_template_name: str,
                                work_directory: str, current_spinup_phase: int,
                                replicate: int = None ) -> str:
    """
    Create a spinup run directory and copy the template files to it.

    Parameters:
    bern3d_template_path (str): Path to the template files.
    bern3d_template_name (str): Name of the template files.
    work_directory (str): Path to the work directory.
    current_spinup_phase (int): Current spinup phase.

    Returns:
    str: Path to the new simulation directory.
    """

    # copy the whole directory
    if replicate is not None:
        new_name = f"Spinup{current_spinup_phase}_{replicate}"
    else:
        new_name = f"Spinup{current_spinup_phase}"

    new_simulation_path = Path(work_directory) / f"run_{new_name}"
    shutil.copytree(bern3d_template_path, new_simulation_path, dirs_exist_ok=True)

    # In the parent directory, create an empty directory called results
    results_dir = Path(work_directory) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Replace old_name with new_name in specific files
    files_to_edit = ["parallel.sh", "parallel_investor.sh", f"{bern3d_template_name}.main.parameter"]
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


def save_config_as_assignment(config: ConfigMainParameters, config_file_path: str) -> None:

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