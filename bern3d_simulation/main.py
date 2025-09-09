#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is used to launch a simulation, and ensure it finishes in case of timeout or crashes.
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
import simulation.utils as sim
import bern3d_tools.shared.utils as shared_utils

def main(config_file: str, initial_submission: bool, email: str) -> None:
    """
    This function is used to launch a simulation, and ensure it finishes in case of timeout or
    crashes.

    Parameters:
    config_file (str): Path to the configuration file
    initial_submission (bool): Flag to indicate if this is the first submission of the job

    Returns:
    None
    """

    # Load the configuration file
    my_config = shared_utils.read_config_file(config_file, sim.JobConfig)
    my_config = sim.check_configuration(my_config)

    if initial_submission:
        logging.info("Initial submission of the job.")
        # copy the job to the work directory
        run_directory = shared_utils.setup_run_directory(template_dir=my_config.bern3d_template,
                                                    executable_name=my_config.bern3d_executable_name,
                                                    new_name=my_config.simulation_name,
                                                    work_dir=my_config.work_directory,
                                                    restart_files=my_config.bern3d_restart_files)

    else:

        # Check if job finished
        run_directory = f"{my_config.work_directory}/run"
        simulation_status = sim.check_simulation_status(run_directory,
                                                        my_config.simulation_name)

        if simulation_status:
            logging.info("Job finished successfully.")
            return

    logging.info("(Re)starting the simulation...")
    sim_id = shared_utils.submit_job(my_config.bern3d_submit_script, my_config.simulation_name,
                                     run_directory, my_config.time_bern3d,
                                     header_command=f"--mail-user={email}")

    # Launch dependent job
    command_line_arguments = [my_config.config_file, "--restart", email]
    executable_name = f"{my_config.main_script}/main.py"

    shared_utils.submit_job(my_config.python_script, executable_name,
                   my_config.main_script, my_config.time_python,
                   header_command=f"--mail-user={email}",
                   dependency=[sim_id], dependency_type='afterany',
                    command_line_arg = command_line_arguments)

if __name__ == "__main__":
    # Example usage:
    # python main.py --config_file ./config_files/config.yaml --initial_submission

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run the model spinup.")
    parser.add_argument("--config_file", required=True, type=str,
                        help='Path to the configuration file')
    parser.add_argument('--initial_submission', dest='initial_submission',
                        action='store_true', help='Set the flag value to True.')
    parser.add_argument('--restart', dest='initial_submission', action='store_false',
                        help='Set the flag value to False.')
    parser.add_argument("--email", required=False, type=str,
                        help='Email address for job notifications')
    parser.set_defaults(initial_submission=False)

    args = parser.parse_args()

    # if args.email is None, the username is taken from the system
    if args.email is None:
        args.email = shared_utils.get_user_email()

    main(args.config_file, args.initial_submission, args.email)
