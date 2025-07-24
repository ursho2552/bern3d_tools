#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the main script for the sensitivity analysis module.
"""
# Add the grand-parent directory to the sys.path to import functions from the shared module
import sys
import os
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.append(repo_root)

import argparse

import numpy as np
import pathlib as Path
import sensitivity as sa
import bern3d_tools.shared.utils as shared_utils

def main(configureation_file: str, email: str, analyze_runs: bool = False) -> None:
    """
    Main function to run the sensitivity analysis.

    Parameters:
    configureation_file (str): Path to the configuration file.
    email (str): Email address for notifications.

    Returns:
    None
    """
    # Load configuration
    my_config = shared_utils.read_config_file(configureation_file, sa.ConfigParameters)
    my_config = sa.check_configuration(my_config)

    if not analyze_runs:
        # For each parameter create a new parameter file and executable
        model_jobs = []
        parameter_list = [param.strip() for param in my_config.parameter_list.split(",")]
        for parameter in parameter_list:

            for i in range(2):
                # Define the new name for the executable
                # First a decrease in parameter value
                factor = 1 + my_config.relative_change
                if i == 0:
                    factor = 1 - my_config.relative_change

                new_name = f"Low_{parameter}" if i == 0 else f"High_{parameter}"

                # Copy the template executable and parameter file
                run_directory = sa.setup_run_directory(template_dir=my_config.bern3d_template,
                                                executable_name=my_config.bern3d_executable_name,
                                                new_name=new_name,
                                                work_dir=my_config.work_directory,
                                                restart_files=my_config.bern3d_restart_files,
                                                    parameter={parameter: factor})

                # Update the parameter file with the new parameter value
                # get current parameter values
                param_file = f"{run_directory}/{new_name}{my_config.bern3d_parameter_file}"
                parameter_dict = sa.parse_to_dict(file_path=param_file)

                # Adapt value
                parameter_dict = sa.adapt_dictionary(config_dict=parameter_dict,
                                                parameter=parameter,
                                                factor=factor)
                # Create new parameter file
                new_param_file = sa.create_new_parameter_file(config_dict=parameter_dict,
                                                        parameter_file_name=param_file)

                # Submit the job
                model_job_id = shared_utils.submit_job(script_template=my_config.sensitivity_script,
                                                    executable_name=new_name,
                                                    executable_path=run_directory,
                                                    time=my_config.time,
                                                    header_command=f"--mail-user={email}"
                                                    )
                model_jobs.append(model_job_id)

    else:
        # Analyze the runs
        # This part would typically involve checking the results of the runs,
        # comparing them, and possibly generating some output files or reports.
        # For now, we will just print a message indicating that analysis is being performed.
        print("Analyzing runs... (This part is not implemented yet)")


if __name__ == "__main__":
    # Usage:
    # python main.py --configuration_name config_files/sensitivity_setup.yaml

    parser = argparse.ArgumentParser(description="Run sensitivity analysis for BERN3D model.")
    parser.add_argument("--configuration_name", required=True,
                        type=str, help="Path to the configuration file.")
    parser.add_argument("--email", required=False, type=str,
                        help="Email address for notifications.")
    parser.add_argument("--analyze_runs", required=False,
                        action='store_true',
                        help="Flag to analyze runs instead of creating new ones.")
    args = parser.parse_args()

    if args.email is None:
        args.email = shared_utils.get_user_email()

    main(args.configuration_name, args.email, args.analyze_runs)
