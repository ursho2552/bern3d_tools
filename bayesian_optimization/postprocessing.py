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
    new_df, my_optimizer = bo.compute_and_tell_optimizer(optimizer = my_optimizer,
                                                target = my_config.tuning_target,
                                                parameter_list = parameter_list,
                                                simulation_dict = simulation_dictionary,
                                                validation_data_path = my_config.validation_data_path,
                                                parameter_file_template = my_config.bern3d_parameter_file,
                                                **my_config.target_values)

    if first_iteration:
        updated_df = new_df
        # check if index row of new_df contains the word Reference
        if "Reference" in new_df.index[0]:
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
    # python postprocessing.py --config_file bayesian_optimization/config_salt_temp_ida_amoc.yaml --simulation_name Reference,Wind_00_000,Wind_01_000,Wind_02_000,Wind_03_000,Wind_04_000,Wind_05_000,Wind_06_000,Wind_07_000,Wind_08_000,Wind_09_000,Wind_10_000,Wind_11_000,Wind_12_000,Wind_13_000,Wind_14_000,Wind_15_000,Wind_16_000,Wind_17_000,Wind_18_000,Wind_19_000,Wind_20_000,Wind_21_000,Wind_22_000,Wind_23_000,Wind_24_000,Wind_25_000,Wind_26_000,Wind_27_000,Wind_28_000,Wind_29_000
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Postprocessing for Bayesian optimization module')
    parser.add_argument('--config_file', required=True, type=str,
                        help='Name of the configuration file')
    parser.add_argument('--simulation_name', required=True, type=str,
                        help='Name of the simulation files from which the results are fetched')

    command_line_args = parser.parse_args()

    main(command_line_args.config_file, command_line_args.simulation_name)
