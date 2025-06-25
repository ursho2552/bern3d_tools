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
    if not os.path.exists(f"{my_config.output_dir_optimizer}/{my_config.isotope}_df.csv"):
        first_iteration = True

    with open(f"{my_config.output_dir_optimizer}/optimizer.pkl",'rb') as my_optimizer_file:
        my_optimizer = pickle.load(my_optimizer_file)

    # get simulation results
    simulation_names = simulation_names.split(",")
    simulation_dictionary = bo.access_file(model_output_files = my_config.output_files_bern3d,
                                    simulation_name = simulation_names,
                                    output_type = my_config.output_type_bern3d,
                                    output_timescale = my_config.output_timescale_bern3d)

    parameter_list = list(my_config.parameter_mapping.keys())
    new_df, my_optimizer = bo.compute_and_tell_optimizer(optimizer = my_optimizer,
                                                target = my_config.isotope,
                                                parameter_list = parameter_list,
                                                simulation_dict = simulation_dictionary,
                                                validation_data_path = my_config.validation_data_path,
                                                parameter_file_template = my_config.parameter_file,
                                                target_amoc = my_config.target_amoc)

    if first_iteration:
        updated_df = new_df
        my_optimizer.first_error = my_optimizer.get_result().fun
        my_optimizer.last_error = my_optimizer.first_error
    else:
        # Load the existing dataframe
        current_df = pd.read_csv(f"{my_config.output_dir_optimizer}/{my_config.isotope}_df.csv",
                                 index_col=0)

        updated_df = pd.concat([current_df, new_df])

    updated_df.to_csv(f"{my_config.output_dir_optimizer}/{my_config.isotope}_df.csv")

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
    # python postprocessing.py --configuration_name bayesian_optimization/config_simulation.yaml --simulation_name Bay_wind_00_000,Bay_wind_01_000,Bay_wind_02_000,Bay_wind_03_000,Bay_wind_04_000
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Postprocessing for Bayesian optimization module')
    parser.add_argument('--configuration_name', required=True, type=str,
                        help='Name of the configuration file')
    parser.add_argument('--simulation_name', required=True, type=str,
                        help='Name of the simulation files from which the results are fetched')

    command_line_args = parser.parse_args()

    main(command_line_args.configuration_name, command_line_args.simulation_name)
