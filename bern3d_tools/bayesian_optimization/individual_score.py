#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This file performs all postprocessing steps.
"""

import argparse
import pickle
import logging

from skopt import Optimizer

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

    # Create new optimizer
    n_initial_points = my_config.n_initialization
    initial_point_generator = my_config.initialization_type
    parameter_bounds = list(my_config.parameter_bounds.values())
    my_optimizer = Optimizer(parameter_bounds,
                        base_estimator=my_config.surrogate_type,
                        acq_func=my_config.acquisition_type,
                        acq_optimizer=my_config.acquisitition_optimizer,
                        n_jobs=my_config.job_number,
                        n_initial_points=n_initial_points,
                        initial_point_generator=initial_point_generator)


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


    new_df.to_csv(f"{my_config.output_dir_optimizer}/{my_config.tuning_target}_df.csv")


    with open(f"{my_config.output_dir_optimizer}/optimizer_individual.pkl",'wb') as my_optimizer_file:
        pickle.dump(my_optimizer, my_optimizer_file)

# ======================
# Main Function
# ======================
if __name__ in "__main__":

    # Parse command line arguments
    # python postprocessing.py --config_file bayesian_optimization/config_salt_temp_ida_amoc_test.yaml --simulation_name Wind_00_001,Wind_01_001,Wind_02_001,Wind_03_001,Wind_04_001,Wind_05_001,Wind_06_001,Wind_07_001,Wind_08_001,Wind_09_001,Wind_10_001,Wind_11_001,Wind_12_001,Wind_13_001,Wind_14_001,Wind_15_001,Wind_16_001,Wind_17_001,Wind_18_001,Wind_19_001,Wind_20_001,Wind_21_001,Wind_22_001,Wind_23_001,Wind_24_001,Wind_25_001,Wind_26_001,Wind_27_001,Wind_28_001,Wind_29_001,Wind_30_001,Wind_31_001,Wind_32_001,Wind_33_001,Wind_34_001,Wind_35_001,Wind_36_001,Wind_37_001,Wind_38_001,Wind_39_001,Wind_40_001,Wind_41_001,Wind_42_001,Wind_43_001,Wind_44_001,Wind_45_001,Wind_46_001,Wind_47_001,Wind_48_001,Wind_49_001
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Postprocessing for Bayesian optimization module')
    parser.add_argument('--config_file', required=True, type=str,
                        help='Name of the configuration file')
    parser.add_argument('--simulation_name', required=True, type=str,
                        help='Name of the simulation files from which the results are fetched')

    command_line_args = parser.parse_args()

    main(command_line_args.config_file, command_line_args.simulation_name)
