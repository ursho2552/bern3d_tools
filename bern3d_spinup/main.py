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

        # Copy the template executable and parameter file
        new_name = f"Spinup{spinup_phase}"
        run_directory = shared_utils.setup_run_directory(template_dir=my_config.bern3d_template,
                                                         executable_name=my_config.bern3d_executable_name,
                                                         new_name=new_name,
                                                         work_dir=my_config.work_directory,
                                                         restart_files=my_config.bern3d_restart_files)

        # Load the configuration of the spinup phase
        spinup_executable_template = my_config.sbatch_script[f"phase{spinup_phase}"]

        # Load the spinup configuration
        parameter_file = f"{my_config.work_directory}/run/{new_name}.main.parameter"
        parameter_dict = shared_utils.parse_to_dict(file_path=parameter_file, reset=True)

        # Adapt values in the parameter file
        for phase in range(1, spinup_phase + 1):
            phase_dictionary = sp.override_dictionary[f"phase_{phase}"]
            parameter_list = list(phase_dictionary.keys())
            parameter_values = list(phase_dictionary.values())

            parameter_dict = shared_utils.adapt_dictionary(config_dict=parameter_dict,
                                                           parameter=parameter_list,
                                                           factor=None,
                                                           new_value=parameter_values)

        # Create new parameter file
        _ = shared_utils.create_new_parameter_file(config_dict=parameter_dict,
                                                   parameter_file_name=parameter_file)

        # Start the simulation with potential dependencies
        dependency = None
        if spinup_phase > my_config.current_phase:
            dependency = [model_job_id]

        spinup_executable = f"Spinup{spinup_phase}"
        model_job_id = shared_utils.submit_job(script_template=spinup_executable_template,
                                               executable_name=spinup_executable,
                                               executable_path=run_directory,
                                               time=my_config.time,
                                               header_command=f"--mail-user={email}",
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
        args.email = shared_utils.get_user_email()

    main(args.config_file, args.email)
