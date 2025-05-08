#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file initializes the `bern3d_spinup` module.
"""

import argparse
import spinup as sp

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
    my_config = sp.read_config_file(configuration_file, sp.JobConfig)

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
        model_job_id = sp.submit_job(script_template=spinup_executable_template,
                                        executable_name=spinup_executable,
                                        executable_path=run_directory,
                                        time=my_config.time,
                                        header_command=f"--mail-user=={email}",
                                        dependency=dependency)


if __name__ == "__main__":
    # Usage:
    # python main.py --config_file /path/to/config_file.yaml --email username@mail.com

    parser = argparse.ArgumentParser(description="Run the model spinup.")
    parser.add_argument("--config_file", required=True, type=str,
                        help='Path to the configuration file')
    parser.add_argument("--email", required=False, type=str,
                        help='Email address for job notifications')

    args = parser.parse_args()

    # if args.email is None, ask the user for the email address
    if args.email is None:
        args.email = input("Please enter your email address: ")

    main(args.config_file, args.email)
