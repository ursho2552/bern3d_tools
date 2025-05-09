#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file initializes the `bern3d_spinup` module.
"""
# ==================================================================================================
# Add the grand-parent directory (repo root) to sys.path to import functions from the shared module
# ==================================================================================================
import os, sys
# add the grand-parent dir (repo root) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import getpass
import logging
import argparse
import spinup as sp

import bern3d_tools.shared.utils as shared_utils

def main(configuration_file: str, email: str) -> None:
    """
    This is the main function for the spinup module.
    It handles the spinup process of the model.

    Parameters:
    configuration_file (str): Path to the configuration file.
    email (str): Email address for job notifications.

    Returns:
    None
    """

    # Load the configuration file
    my_config = shared_utils.read_config_file(configuration_file, sp.JobConfig)
    # Check if the configuration file is valid
    my_config = sp.check_configuration(my_config)

    for spinup_phase in range(my_config.current_phase, my_config.spinup_phases + 1):

        # Load the configuration of the spinup phase
        spinup_executable_template = getattr(my_config, f"sbatch_script_phase{spinup_phase}")

        # Load the spinup configuration
        parameter_file = f"{my_config.bern3d_template}/{my_config.bern3d_executable_name}.main.parameter"
        spinup_config = sp.get_main_config_fields(parameter_file, sp.override_dictionary,
                                                  spinup_phase)

        # Create a new directory for the spinup phase
        run_directory = sp.create_spinup_run_directory(my_config.bern3d_template,
                                                       my_config.bern3d_executable_name,
                                                       my_config.work_directory,
                                                       spinup_phase)

        # Change the main parameter file
        main_param_file = f"{run_directory}/Spinup{spinup_phase}.main.parameter"
        sp.save_config_as_assignment(spinup_config, main_param_file)

        # Start the simulation with potential dependencies
        dependency = None
        if spinup_phase > my_config.current_phase:
            dependency = [model_job_id]

        spinup_executable = f"Spinup{spinup_phase}"
        model_job_id = shared_utils.submit_job(script_template=spinup_executable_template,
                                        executable_name=spinup_executable,
                                        executable_path=run_directory,
                                        time=my_config.time,
                                        header_command=f"--mail-user=={email}",
                                        dependency=dependency)


if __name__ == "__main__":
    # Usage:
    # python main.py --config_file /path/to/config_file.yaml --email username@mail.com

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run the model spinup.")
    parser.add_argument("--config_file", required=True, type=str,
                        help='Path to the configuration file')
    parser.add_argument("--email", required=False, type=str,
                        help='Email address for job notifications')

    args = parser.parse_args()

    # if args.email is None, the username is taken from the system
    if args.email is None:
        username = getpass.getuser()
        args.email = f"{username}@unibe.ch"

    main(args.config_file, args.email)
