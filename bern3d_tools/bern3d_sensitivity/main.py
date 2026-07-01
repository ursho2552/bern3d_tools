#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the main script for the sensitivity analysis module.
"""

import argparse
import logging
import sensitivity as sa
import bern3d_tools.shared.utils as shared_utils

def main(configuration_file: str, email: str, analyze_runs: bool = False) -> None:
    """
    Main function to run the sensitivity analysis.

    Parameters:
    configureation_file (str): Path to the configuration file.
    email (str): Email address for notifications.

    Returns:
    None
    """
    # Load configuration
    my_config = shared_utils.read_config_file(configuration_file, sa.ConfigParameters)
    my_config = sa.check_configuration(my_config)

    parameter_factor_dict = my_config.parameter_list
    parameter_factor_dict['Reference'] = 1.0

    if not analyze_runs:
        # For each parameter create a new parameter file and executable
        model_jobs = []
        for key, item in parameter_factor_dict.items():

            if key == "Reference":
                sample = {"Reference": {"values": [None],
                                        "factors": [1.0],
                                        "parameters": [None],}
                }


            elif isinstance(item, float) or isinstance(item, int):
                sample = {f"Low_{key}": {"values": [None],
                                              "factors": [1 - item],
                                              "parameters": [key]},
                          f"High_{key}": {"values": [None],
                                               "factors": [1 + item],
                                               "parameters": [key]}
                          }

            elif isinstance(item, list):
                sample = {f"{str(value).replace('.','p')}_{key}": {"values": [value],
                                                                          "factors": [None],
                                                                          "parameters": [key]}
                          for value in item}


            elif isinstance(item, dict):
                sample = {}
                for i in range(len(next(iter(item.values())))):
                    name = f"Multiparam_{key}_{i}"
                    values = [item[param][i] for param in item.keys()]
                    sample[name] = {"values": values,
                                    "factors": [None] * len(values),
                                    "parameters": list(item.keys())}

            elif item is None:
                sample = {f"Low_{key}": {"values": [None],
                                              "factors": [1 - my_config.relative_change],
                                              "parameters": [key]},
                          f"High_{key}": {"values": [None],
                                               "factors": [1 + my_config.relative_change],
                                               "parameters": [key]}
                          }

            # Copy the template executable and parameter file
            for new_name, sample_items in sample.items():
                factors = sample_items["factors"]
                values = sample_items["values"]
                parameters = sample_items["parameters"]

                run_directory = shared_utils.setup_run_directory(template_dir=my_config.bern3d_template,
                                                    executable_name=my_config.bern3d_executable_name,
                                                    new_name=new_name,
                                                    work_dir=my_config.work_directory,
                                                    restart_files=my_config.bern3d_restart_files)

                list_parameter_files = my_config.bern3d_parameter_file.split(",")
                for param_file_template in list_parameter_files:

                    full_path = f"{run_directory}/{new_name}{param_file_template}"
                    parameter_dict, preserved_lines = shared_utils.parse_to_dict(file_path=full_path)

                    # Adapt values
                    for param, value, factor in zip(parameters, values, factors):
                        parameter_dict = shared_utils.adapt_dictionary(config_dict=parameter_dict,
                                                        parameter=param,
                                                        factor=factor,
                                                        new_value=value)

                    # Create new parameter file
                    _ = shared_utils.create_new_parameter_file(config_dict=parameter_dict,
                                                            parameter_file_name=full_path,
                                                            preserved_lines=preserved_lines)

                # Submit the job
                model_job_id = shared_utils.submit_job(script_template=my_config.bern3d_run_script,
                                                    executable_name=new_name,
                                                    executable_path=run_directory,
                                                    time=my_config.time_bern3d,
                                                    header_command=f"--mail-user={email}"
                                                    )
                model_jobs.append(model_job_id)

        # Launch dependent job for evaluation
        command_line_arg = [f"{my_config.main_script_path}/{configuration_file}"]
        executable_name = f"{my_config.main_script_path}/main.py"

        _ = shared_utils.submit_job(script_template=my_config.evaluation_script,
                                    executable_name=executable_name,
                                    executable_path=my_config.work_directory,
                                    time=my_config.time_evaluation,
                                    header_command=f"--mail-user={email}",
                                    dependency=model_jobs,
                                    dependency_type="afterany",
                                    command_line_arg=command_line_arg)

    else:
        # Analyze results
        logging.info("Analyzing runs...")
        results_df = sa.analyze_sensitivity_results(my_config, parameter_factor_dict)

        # Save results
        sa.save_sensitivity_summary(results_df, my_config.work_directory)
        logging.info("Sensitivity analysis complete!")

if __name__ == "__main__":
    # Usage:
    # python main.py --config_file config_files/sensitivity_setup.yaml
    parser = argparse.ArgumentParser(description="Run sensitivity analysis for BERN3D model.")
    parser.add_argument("--config_file", required=True,
                        type=str, help="Path to the configuration file.")
    parser.add_argument("--email", required=False, type=str,
                        help="Email address for notifications.")
    parser.add_argument("--analyze_runs", required=False,
                        action='store_true',
                        help="Flag to analyze runs instead of creating new ones.")
    args = parser.parse_args()

    if args.email is None:
        args.email = shared_utils.get_user_email()

    main(args.config_file, args.email, args.analyze_runs)
