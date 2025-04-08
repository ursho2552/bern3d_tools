#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script is used to launch a simulation, and ensure it finishes in case of timeout or crashes.
"""
import logging
import argparse
import simulation.utils as sim

def main(config_file: str, initial_submission: bool) -> None:
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
    my_config = sim.read_config_file(config_file)

    if initial_submission:
        logging.info("Initial submission of the job.")
        # copy the job to the work directory
        new_path = sim.create_simulation_run_directory(my_config.bern3d_template,
                                            my_config.bern3d_executable_name,
                                            my_config.work_directory,
                                            my_config.simulation_name)

    else:

        # Check if job finished
        new_path = f"{my_config.work_directory}/run_{my_config.simulation_name}"
        simulation_status = sim.check_simulation_status(new_path,
                                                        my_config.simulation_name)

        if simulation_status:
            logging.info("Job finished successfully.")
            return

    logging.info("(Re)starting the simulation...")
    sim_id = sim.submit_job(my_config.bern3d_submit_script, my_config.simulation_name,
                                new_path, my_config.time_bern3d)

    # Launch dependent job
    command_line_arguments = [my_config.config_file, "--restart"]
    executable_name = f"{my_config.main_script}/main.py"
    sim.submit_job(my_config.python_script, executable_name,
                    my_config.main_script, my_config.time_python, dependency=[sim_id],
                    command_line_arg = command_line_arguments,
                    dependency_type='afterany')

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
    parser.set_defaults(initial_submission=False)
    args = parser.parse_args()

    main(args.config_file, args.initial_submission)
