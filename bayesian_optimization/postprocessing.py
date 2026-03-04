#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file performs all postprocessing steps.
"""
import os, sys
# add the grand-parent dir (repo root) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import argparse
import pickle
import logging

import pandas as pd
import bayesian_optimization as bo
import bern3d_tools.shared.utils as shared_utils

def main(configuration_file, simulation_names) -> None:
    """
    Main function for postprocessing after running Bern3D simulations.

    Parameters:
    configuration_file (str): Path to the configuration file.
    simulation_names (str): Comma-separated list of simulation names.

    Returns:
    None
    """

    # Load the configuration file
    my_config = shared_utils.read_config_file(configuration_file, bo.ConfigParameters)
    my_config = bo.check_configuration(my_config)

    # Load the parameter iteration and optimizer
    # Check if the file exists
    first_iteration = False
    if not os.path.exists(f"{my_config.output_dir_optimizer}/{my_config.tuning_target}_df.csv"):
        first_iteration = True

    with open(f"{my_config.output_dir_optimizer}/optimizer.pkl",'rb') as my_optimizer_file:
        my_optimizer = pickle.load(my_optimizer_file)

    # get simulation results
    simulation_names = simulation_names.split(",")
    simulation_dictionary = bo.access_file(model_output_files = my_config.output_files_bern3d,
                                    simulation_name = simulation_names,
                                    output_type = my_config.output_type_bern3d,
                                    output_timescale = my_config.output_timescale_bern3d)

    parameter_list = list(my_config.parameter_bounds.keys())
    function_kwargs = {
                'variable_names': my_config.variable_names,
                'use_penalty': my_config.use_penalty,
                **my_config.target_values
                }

    new_df, my_optimizer = bo.compute_and_tell_optimizer(optimizer = my_optimizer,
                                                target = my_config.tuning_target,
                                                parameter_list = parameter_list,
                                                simulation_dict = simulation_dictionary,
                                                validation_data_path = my_config.validation_data_path,
                                                parameter_file_template = my_config.bern3d_parameter_file,
                                                **function_kwargs)

    if first_iteration:
        updated_df = new_df
        # check if index row of new_df contains the word Reference *(my_config.use_reference_simulation)
        if ("Reference" in new_df.index[0])*(my_config.use_reference_simulation):
            # use the error of the reference simulation as first error
           first_error = new_df.iloc[0][-1]
        else:
            # use the mean of the function values as first error
            first_error = my_optimizer.get_result().func_vals.mean()
        my_optimizer.first_error = first_error
        my_optimizer.last_error = my_optimizer.first_error
        my_optimizer.stable_iterations = 0
    else:
        # Load the existing dataframe
        current_df = pd.read_csv(f"{my_config.output_dir_optimizer}/{my_config.tuning_target}_df.csv",
                                 index_col=0)

        updated_df = pd.concat([current_df, new_df])

    updated_df.to_csv(f"{my_config.output_dir_optimizer}/{my_config.tuning_target}_df.csv")

    #update last error of optimizer to check stability
    if my_optimizer.get_result().fun < my_optimizer.last_error:
        my_optimizer.last_error = my_optimizer.get_result().fun
        my_optimizer.stable_iterations = 0
    else:
        my_optimizer.stable_iterations += 1

    with open(f"{my_config.output_dir_optimizer}/optimizer.pkl",'wb') as my_optimizer_file:
        pickle.dump(my_optimizer, my_optimizer_file)

# ======================
# Main Function
# ======================
if __name__ in "__main__":

    # Parse command line arguments
    # python postprocessing.py --config_file bayesian_optimization/config_salt_temp_ida_amoc.yaml --simulation_name Wind_00_001,Wind_01_001,Wind_02_001,Wind_03_001,Wind_04_001,Wind_05_001,Wind_06_001,Wind_07_001,Wind_08_001,Wind_09_001,Wind_10_001,Wind_11_001,Wind_12_001,Wind_13_001,Wind_14_001,Wind_15_001,Wind_16_001,Wind_17_001,Wind_18_001,Wind_19_001,Wind_20_001,Wind_21_001,Wind_22_001,Wind_23_001,Wind_24_001,Wind_25_001,Wind_26_001,Wind_27_001,Wind_28_001,Wind_29_001
    # python postprocessing.py --config_file bayesian_optimization/config_salt_temp_ida_amoc.yaml --simulation_name Wind_00_001,Wind_01_001,Wind_02_001,Wind_03_001,Wind_04_001,Wind_05_001,Wind_06_001,Wind_07_001,Wind_08_001,Wind_09_001
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Postprocessing for Bayesian optimization module')
    parser.add_argument('--config_file', required=True, type=str,
                        help='Name of the configuration file')
    parser.add_argument('--simulation_name', required=True, type=str,
                        help='Name of the simulation files from which the results are fetched')

    command_line_args = parser.parse_args()

    main(command_line_args.config_file, command_line_args.simulation_name)
