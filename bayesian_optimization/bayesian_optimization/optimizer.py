#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the optimizer script for the Bayesian optimization module.
"""
import os

import re
import logging
from typing import Union

from pathlib import Path
import pandas as pd
import xarray as xr
import numpy as np
from skopt import Optimizer

from .scoring.targets import TargetRegistry


def calculate_score_df(target: str, parameter_list: list[str],
                       model_xr: dict[str, xr.Dataset], sims: list[str],
                       validation_data_path: str,
                       parameter_files: list[str],
                       log_files: list[str],
                       **kwargs: float) -> pd.DataFrame:
    """ Calculate the parameter dataframe for a given target and multiple simulations.

        Parameters:
            target (str): Target type ("Pad", "Thd", "Temperature", "Salinity").
            parameter_list (list): List of parameters to calculate.
            model_xr (dict): Dictionary of model datasets.
            sims (list): List of simulation names.
            validation_data_path (str): Path to the validation data.
            parameter_files (list): list of paths to the parameter files.
            log_files (list): list of paths to the log files.
            **kwargs: Additional keyword arguments for scoring.

        Returns:
            pd.DataFrame: Dataframe with calculated parameters and score for all simulations.
    """

    # Map old target strings to registry names
    if target in ["Pad", "Thd"]:
        registry_name = "isotope"
    elif any(t in target.lower() for t in ["temp", "salt", 'amoc', 'ida']):
        registry_name = "temp_salt_ida_amoc"
    elif any(t in target.lower() for t in ["dic", "alk", "po4", "sio", "no3", "poc", "caco3",
                                           "opal", "npp"]):
        registry_name = "npzd"
    else:
        raise ValueError("Target must be the isotopes 'Pad' and/or 'Thd', the variables 'temp'"
                         " and/or 'salt', or the variables 'dic', 'alk', 'po4', 'sio', 'poc', "
                         " 'caco3', 'opal', 'npp'.")

    # Create target instance and score
    scoring_target = TargetRegistry.create(registry_name, name=target)
    param_df = scoring_target.score(
        parameter_list=parameter_list,
        model_xr=model_xr,
        sims=sims,
        validation_data_path=validation_data_path,
        parameter_files=parameter_files,
        log_files=log_files,
        **kwargs
    )
    return param_df

def correct_failed_simulations(optimizer: Optimizer, df: pd.DataFrame,
                               target: str, standard_penalty: float = 2.0) -> list[float]:
    """
    Correct the target values in the dataframe for failed simulations.
    If a simulation failed, it is assigned a penalty value.

    Parameters:
    optimizer (Optimizer): Optimizer instance.
    df (pd.DataFrame): Dataframe containing the target values.
    target (str): Target type.
    standard_penalty (float): Standard penalty value for failed simulations (Default is 4.0)
    Returns:
    list: List of corrected target values.
    """

    # Get penalty for failed simulations
    target_values = df[f"mae_{target.lower()}"].values
    target_values[target_values == 1e6] = np.nan
    penalty = standard_penalty*np.nanmean(target_values)

    try:
        error_values = optimizer.get_result().func_vals
        if len(error_values) >= optimizer.get_result().specs['args']['n_initial_points']:
            penalty = standard_penalty*np.mean(error_values)
    except:
        penalty = standard_penalty*np.nanmean(target_values)

    # Add a soft-penalty for failed simulations
    print(f"Using a penalty of {penalty} for failed simulations.")
    corrected_target = np.where(np.isnan(target_values), penalty, target_values)

    return corrected_target.tolist()


def compute_and_tell_optimizer(optimizer: Optimizer, target: str,
                               parameter_list: list[str],
                               simulation_dict: dict[str, xr.Dataset],
                               validation_data_path: str,
                               parameter_file_template: str,
                               **kwargs: float) -> tuple[pd.DataFrame, list]:
    """
    Compute the mean absolute error (MAE) and update the optimizer.

    Parameters:
    optimizer (Optimizer): Optimizer instance.
    target (str): target type ("Pad" or "Thd").
    parameter_list (list): List of parameters to calculate.
    simulation_dict (dict): Dictionary of simulation datasets.
    validation_data_path (str): Path to the validation data.
    parameter_file_template (str): Template for the parameter file name.
    target_amoc (float): Target AMOC value (optional).

    Returns:
    tuple: Dataframe with calculated parameters and score for all simulations and updated optimizer.
    """

    use_penalty = kwargs.get('use_penalty', False)

    if not isinstance(parameter_list, list):
        parameter_list = [parameter_list]

    simulation_names = list(simulation_dict.keys())
    # construct the parameter file name
    # should be in the run directory of the simulation

    parameter_files = []
    log_files = []

    for sim in simulation_names:
        root_dir = Path(sim).parent.parent
        name_sim = Path(sim).name.split(".")[0]
        # paramter_file_template may contain multiple parts separated by ,
        list_parameter_file_template = parameter_file_template.split(",")
        # create multiple name_param for each item in list_parameter_file_template
        # check if runs are in run_{name_sim} or run
        if os.path.exists(f"{root_dir}/run_{name_sim}/"):
            # parameter_files.append(f"{root_dir}/run_{name_sim}/{name_param}")
            current_param_list = [f"{root_dir}/run_{name_sim}/{name_sim}{part}" for part in list_parameter_file_template]
            parameter_files.append(current_param_list)
            log_files.append(f"{root_dir}/run_{name_sim}/{name_sim}.out")
        else:
            # parameter_files.append(f"{root_dir}/run/{name_param}")
            current_param_list = [f"{root_dir}/run/{name_sim}{part}" for part in list_parameter_file_template]
            parameter_files.append(current_param_list)
            log_files.append(f"{root_dir}/run/{name_sim}.out")

    test_df = calculate_score_df(target, parameter_list, simulation_dict, simulation_names,
                                 validation_data_path, parameter_files, log_files, **kwargs)

    # Remove reference in test_df if it exists
    test_df_clean = test_df.copy()
    for index_str in test_df.index:
        if "Reference" in index_str:
            test_df_clean = test_df.drop(index=index_str)
            break

    if use_penalty:
        # Add penalty to failed simulations
        corrected_mae = correct_failed_simulations(optimizer, test_df_clean, target)
        tested_parameters = test_df_clean[parameter_list].values.tolist()

    else:
        # Simply remove failed simulations
        target_values = test_df_clean[f"mae_{target.lower()}"].values
        failed_mask = target_values == 1e6
        successful_indices =  failed_mask == False
        if np.any(successful_indices):
            test_df_clean = test_df_clean[successful_indices]
            tested_parameters = test_df_clean[parameter_list].values.tolist()
            corrected_mae = test_df_clean[f"mae_{target.lower()}"].values.tolist()
            logging.info(f"Removed {np.sum(failed_mask)} failed simulations")
            logging.info(f"Using {len(corrected_mae)} successful simulations")
        else:
            logging.warning("All simulations failed! Cannot update optimizer.")
            return test_df_clean, optimizer

    # Add penalty to failed simulations
    optimizer.tell(tested_parameters, corrected_mae)
    logging.info("Told new parameters to optimizer")

    # Correct indeces to match only simulation names
    corrected_index = []
    for index in test_df_clean.index:
        corrected_index.append(index.split("/")[-1].split(".")[0])

    test_df_clean.index = corrected_index
    test_df_clean[f"mae_{target.lower()}"] = corrected_mae
    # add Reference row at the top if it was removed and write the index as Reference
    for index_str in test_df.index:
        if "Reference" in index_str:
            reference_row = test_df.loc[index_str]
            reference_row.name = "Reference"
            test_df_clean = pd.concat([pd.DataFrame([reference_row]), test_df_clean])
            break

    return test_df_clean, optimizer

def check_optimization_status(optimizer: Optimizer, iteration: int,
                              max_iteration: int = 10) -> bool:

    optimization_done = False
    # Check if the maximum number of iterations has been reached
    if iteration > max_iteration:
        logging.info("Maximum number of iterations reached for the Bayesian optimization")
        optimization_done = True

    # Check if the optimizer has improved in the last max_stable_iterations
    if optimizer.stable_iterations >= optimizer.max_stable_iterations:
        logging.info("Maximum number of stable iterations reached, stopping the optimization")
        optimization_done = True

    return optimization_done
