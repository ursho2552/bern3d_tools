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
import latin_hypercube_sampling as lhs
import bern3d_tools.shared.utils as shared_utils
import matplotlib.pyplot as plt


def main(configuration_file: str, email: str) -> None:
    """
    Main function to run the sensitivity analysis.

    Parameters:
    configureation_file (str): Path to the configuration file.
    email (str): Email address for notifications.

    Returns:
    None
    """
    # Load configuration
    my_config = shared_utils.read_config_file(configuration_file, lhs.ConfigParameters)
    my_config = lhs.check_configuration(my_config)

    num_concurrent_jobs = my_config.num_concurrent_jobs
    num_samples = my_config.num_samples

    # Get parameter list and bounds for each parameter
    parameter_list = list(my_config.parameter_list.keys())
    parameter_factor_dict = my_config.parameter_list

    # Create LHS samples
    samples = lhs.create_lhs_samples(parameter_list=parameter_list,
                                    parameter_factor_dict=parameter_factor_dict,
                                    num_samples=num_samples)

    samples.insert(0, None)

    # for each sample create a new parameter file and executable
    model_jobs = []
    concurrent_jobs = []
    for i, sample in enumerate(samples):

        change_params = True
        if sample is None:
            new_name = "Reference"
            change_params = False
        else:
            # Define the new name for the executable
            new_name = f"Sample_{str(i+1).zfill(3)}"

        # Copy the template executable and parameter file
        run_directory = shared_utils.setup_run_directory(template_dir=my_config.bern3d_template,
                                        executable_name=my_config.bern3d_executable_name,
                                        new_name=new_name,
                                        work_dir=my_config.work_directory,
                                        restart_files=my_config.bern3d_restart_files)

        # Update the parameter file with the new parameter values
        list_parameter_files = my_config.bern3d_parameter_file.split(",")
        for param_file_template in list_parameter_files:

            full_path = f"{run_directory}/{new_name}{param_file_template}"
            parameter_dict, preserved_lines = shared_utils.parse_to_dict(file_path=full_path)

            # Adapt values
            if change_params:
                for param, value in sample.items():
                    parameter_dict = shared_utils.adapt_dictionary(config_dict=parameter_dict,
                                                    parameter=param,
                                                    factor=None,
                                                    new_value=value)

            # Create new parameter file
            _ = shared_utils.create_new_parameter_file(config_dict=parameter_dict,
                                                    parameter_file_name=full_path,
                                                    preserved_lines=preserved_lines)

        # submit the first X jobs
        if i < num_concurrent_jobs:
            model_job_id = shared_utils.submit_job(script_template=my_config.bern3d_run_script,
                                                executable_name=new_name,
                                                executable_path=run_directory,
                                                time=my_config.time_bern3d,
                                                header_command=f"--mail-user={email}"
                                                )
            model_jobs.append(model_job_id)
        else:
            # schedule new batch of X jobs
            model_job_id = shared_utils.submit_job(script_template=my_config.bern3d_run_script,
                                            executable_name=new_name,
                                            executable_path=run_directory,
                                            time=my_config.time_bern3d,
                                            header_command=f"--mail-user={email}",
                                            dependency=model_jobs,
                                            dependency_type="afterany"
                                            )

            concurrent_jobs.append(model_job_id)
            if i%num_concurrent_jobs == (num_concurrent_jobs - 1):
                model_jobs = concurrent_jobs
                concurrent_jobs = []


if __name__ == "__main__":
    # Usage:
    # python main.py --config_file config_files/config_lhs.yaml
    parser = argparse.ArgumentParser(description="Run sensitivity analysis for BERN3D model.")
    parser.add_argument("--config_file", required=True,
                        type=str, help="Path to the configuration file.")
    parser.add_argument("--email", required=False, type=str,
                        help="Email address for notifications.")
    args = parser.parse_args()

    if args.email is None:
        args.email = shared_utils.get_user_email()

    main(args.config_file, args.email)
