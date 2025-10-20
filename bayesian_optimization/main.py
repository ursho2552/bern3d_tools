#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file initializes the `bayesian_optimization` module.
"""
# ==================================================================================================
# Add the grand-parent directory (repo root) to sys.path to import functions from the shared module
# ==================================================================================================
import os, sys
# add the grand-parent dir (repo root) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import argparse
import logging
import pickle

import numpy as np
from skopt import Optimizer
import bayesian_optimization as bo
import bern3d_tools.shared.utils as shared_utils

def main(configuration_file: str, current_iteration: int, email: str) -> None:
    """
    This is the main function for the Bayesian optimization module.

    Parameters:
    configuration_file (str): Path to the configuration file.
    current_iteration (int): Current iteration number.
    email (str): Email address for job notifications.

    Returns:
    None
    """

    # Load the configuration file
    my_config = shared_utils.read_config_file(configuration_file, bo.ConfigParameters)
    my_config = bo.check_configuration(my_config)

    if current_iteration == 0:

        if my_config.initialization_type == "simulation":

            logging.info("Initialize with a simulation")
            n_initial_points = 1
            initial_point_generator = "lhs"
            simulation_initialization = True
            wildcard = my_config.wildcard_simulation

        else:

            logging.info("Initialize with %s", my_config.initialization_type)
            n_initial_points = my_config.n_initialization
            initial_point_generator = my_config.initialization_type
            simulation_initialization = False
            wildcard = None

        parameter_bounds = list(my_config.parameter_bounds.values())

        my_optimizer = Optimizer(parameter_bounds,
                        base_estimator=my_config.surrogate_type,
                        acq_func=my_config.acquisition_type,
                        acq_optimizer=my_config.acquisitition_optimizer,
                        n_jobs=my_config.job_number,
                        n_initial_points=n_initial_points,
                        initial_point_generator=initial_point_generator)

        if my_config.initialization_type == "simulation":

            simulation_dictionary = bo.access_file(model_output_files = my_config.output_files_restart,
                                             simulation_name = my_config.simulation_name_restart,
                                             output_type = my_config.output_type_bern3d,
                                             output_timescale = my_config.output_timescale_bern3d,
                                             simulation_initialization = simulation_initialization,
                                             wildcard = wildcard)

            parameter_list = list(my_config.parameter_bounds.keys())
            # adapt how targets are passed to compute_and_tell_optimizer, since they should be passed as kwargs

            initial_df, my_optimizer = bo.compute_and_tell_optimizer(optimizer = my_optimizer,
                                                                     target = my_config.tuning_target,
                                                                     parameter_list = parameter_list,
                                                                     simulation_dict = simulation_dictionary,
                                                                     validation_data_path = my_config.validation_data_path,
                                                                     parameter_file_template = my_config.bern3d_parameter_file,
                                                                     **my_config.target_values)

            initial_df.to_csv(f"{my_config.output_dir_optimizer}/{my_config.tuning_target}_df_simulations.csv")

    else:
        logging.info("Loading the optimizer from the previous iteration")
        with open(f"{my_config.output_dir_optimizer}/optimizer.pkl", 'rb') as my_optimizer_file:
            my_optimizer = pickle.load(my_optimizer_file)

    #######################################
    ### Ask for next parameters to test ###
    #######################################
    # Vary the number of points to test based on the current iteration and error relative to the
    # first error (if available)
    strategy = "cl_max"
    if not 'first_error' in  dir(my_optimizer):
        logging.info("Asking for initial parameters to test")
        num_points = my_config.batchsize
        my_optimizer.stable_iterations = 0
        my_optimizer.max_stable_iterations = my_config.max_stable_iterations

    else:
        logging.info("Asking for next parameters to test in iteration %d", current_iteration)
        fraction = max(1, my_optimizer.get_result().fun/my_optimizer.first_error)
        num_points = my_config.batchsize*fraction
        num_points = max(int(num_points), 2)
        if fraction < 0.3:
            strategy = "cl_mean"
        elif fraction < 0.1:
            strategy = "cl_min"

    next_parameters = my_optimizer.ask(n_points=num_points, strategy=strategy)
    # Save the optimizer
    with open(f"{my_config.output_dir_optimizer}/optimizer.pkl", 'wb') as my_optimizer_file:
        pickle.dump(my_optimizer, my_optimizer_file)

    if my_config.batchsize == 1:
        next_parameters = [next_parameters]

    my_simulation_ids = []
    my_simulation_names = []
    batch_offset = 0
    if current_iteration == 0 and not my_config.initialization_type == "simulation":
        # extend next parameters by one to account for the reference simulation
        next_parameters.insert(0,None)
        batch_offset = 1

    for batch_number, next_parameter in enumerate(next_parameters):

        if next_parameter is None:
            # first copy the template runscript to the work directory
            my_simulation_name = "Reference"
            template_dir = my_config.bern3d_template
            executable_name = my_config.bern3d_executable_name
            restart_files=my_config.bern3d_restart_files
            fixed_values = []
            names_fixed = []
        else:
            # Create new simulation files with runname equal to my_simulation_name
            my_simulation_name = f"{my_config.simulation_name_bern3d}_{str(batch_number - batch_offset).zfill(2)}_{str(current_iteration).zfill(3)}"
            template_dir = f"{my_config.work_directory}/run/"
            executable_name = "Reference"
            restart_files=None
            fixed_values = list(my_config.fixed_values.values()) if my_config.fixed_values else []
            names_fixed = list(my_config.fixed_values.keys()) if my_config.fixed_values else []

        # Support for Bern3D_F90 only
        new_simulation_path = shared_utils.setup_run_directory(template_dir=template_dir,
                                                               executable_name=executable_name,
                                                               new_name=my_simulation_name,
                                                               work_dir=my_config.work_directory,
                                                               restart_files=restart_files)

        # update parameter files
        # May have multiple paramter files to update in my_config.bern3d_parameter_file
        # these are comma separated
        list_parameter_files = my_config.bern3d_parameter_file.split(",")
        for param_file_template in list_parameter_files:

            param_file = f"{new_simulation_path}/{my_simulation_name}{param_file_template}"
            parameter_dict, preserved_lines = shared_utils.parse_to_dict(file_path=param_file)

            # Adapt value
            # paramter list is taken from parameter_bounds keys
            parameter_names = list(my_config.parameter_bounds.keys())
            parameter_dict = shared_utils.adapt_dictionary(config_dict=parameter_dict,
                                                        parameter=parameter_names,
                                                        factor=1, new_value=next_parameter)
            # set fixed values
            for name, value in zip(names_fixed, fixed_values):
                parameter_dict = shared_utils.adapt_dictionary(config_dict=parameter_dict,
                                                                parameter=[name],
                                                                factor=1,
                                                                new_value=[value])

            # Create new parameter file
            _ = shared_utils.create_new_parameter_file(config_dict=parameter_dict,
                                                    parameter_file_name=param_file,
                                                    preserved_lines=preserved_lines)

        # run the new simulation
        model_job_id = shared_utils.submit_job(script_template=my_config.bern3d_script,
                                               executable_name=my_simulation_name,
                                               executable_path=new_simulation_path,
                                               time=my_config.bern3d_script_time,
                                               header_command=f"--mail-user={email}")

        my_simulation_ids.append(model_job_id)
        my_simulation_names.append(my_simulation_name)

    # Create and run dependent sbatch simulation for post-processing
    # command line arguments for the postprocessing script
    simulation_names = ",".join(my_simulation_names)
    command_line_arg = [my_config.config_file_path, simulation_names]

    executable_name = f"{my_config.python_scripts}/postprocessing.py"
    postprocessing_job_id = shared_utils.submit_job(script_template=my_config.postprocessing_script,
                                        executable_name=executable_name,
                                        executable_path=my_config.work_directory,
                                        time=my_config.postprocessing_script_time,
                                        header_command=f"--mail-user={email}",
                                        dependency=my_simulation_ids,
                                        dependency_type="afterany",
                                        command_line_arg=command_line_arg)

    # call optimizer script for the next iteration
    current_iteration += 1
    command_line_arg = [my_config.config_file_path, str(current_iteration), email]

    optimization_done = bo.check_optimization_status(my_optimizer, current_iteration,
                                                     my_config.max_iterations)

    if not optimization_done:
        # Call optimizer script for the next iteration
        logging.info("Calling the optimizer for the next iteration: %d", current_iteration)
        # Create and run dependent sbatch simulation for post-processing
        executable_name = f"{my_config.python_scripts}/main.py"
        _ = shared_utils.submit_job(script_template=my_config.optimizer_script,
                                            executable_name=executable_name,
                                            executable_path=my_config.work_directory,
                                            time=my_config.optimizer_script_time,
                                            header_command=f"--mail-user={email}",
                                            dependency=[postprocessing_job_id],
                                            command_line_arg=command_line_arg)

# ======================
# Main Function
# ======================
if __name__ in "__main__":

    # python main.py --config_file bayesian_optimization/config_temperature.yaml
    # Parse command line arguments
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Run bayesian optimization')
    parser.add_argument('--config_file', required=True, type=str,
                        help='Path to the configuration file')
    parser.add_argument('--current_iteration', required=False, type=int, default=0,
                        help='Current iteration number (default 0)')
    parser.add_argument("--email", required=False, type=str,
                        help='Email address for job notifications')

    command_line_args = parser.parse_args()

    # if args.email is None, the username is taken from the system
    if command_line_args.email is None:
        command_line_args.email = shared_utils.get_user_email()

    np.random.seed(command_line_args.current_iteration)
    main(command_line_args.config_file, command_line_args.current_iteration,
         command_line_args.email)
