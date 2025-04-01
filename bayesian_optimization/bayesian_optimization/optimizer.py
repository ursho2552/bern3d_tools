#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the optimizer script for the Bayesian optimization module.
"""

import logging
from typing import Union
import concurrent.futures

import pandas as pd
import xarray as xr
import numpy as np
import numpy.typing as npt
from skopt import Optimizer

def find_nearest(array: npt.ArrayLike, value: float,
                 retval: int = 1) -> Union[float, int, tuple[float, int]]:
    """
    Find the nearest value in an array to a given value.

    Parameters:
    array (np.array): Array to search.
    value (float): Value to find the nearest to.
    retval (int): Determines the return value (0: nearest value, 1: index, 2: both).

    Returns:
    float or int or tuple: Nearest value, index, or both.
    """
    # Perform safety checks and convert array to numpy array
    assert retval in [0, 1, 2], "Return value must be 0, 1, or 2."
    assert not np.isnan(value), "Value must not be NaN."
    if not isinstance(array, np.ndarray):
        array = np.asarray(array)

    idx = int((np.abs(array - value)).argmin())
    if retval == 2:
        return array[idx], idx
    if retval == 1:
        return idx

    return array[idx]

def calculate_score_df(isotope: str, parameter_list: list[str],
                       model_xr: dict[str, xr.Dataset], sims: list[str],
                       validation_data_path: str) -> pd.DataFrame:
    """
    Calculate the parameter dataframe for a given isotope and multiple simulations.

    Parameters:
    isotope (str): Isotope type ("Pad" or "Thd").
    parameter_list (list): List of parameters to calculate.
    model_xr (dict): Dictionary of model datasets.
    sims (list): List of simulation names.
    validation_data_path (str): Path to the validation data.

    Returns:
    pd.DataFrame: Dataframe with calculated parameters and score for all simulations.
    """

    assert isotope in ["Pad", "Thd"], "Isotope must be either 'Pad' or 'Thd'."

    # This feels dangerous.
    pd.options.mode.copy_on_write = True

    # Need to avoid using hardcoded paths (leave for now).
    # An option would be to use a config file that stores this information for each run
    isotope_name_d = f'{isotope[:2]}d' # Pad or Thd
    isotope_name_p = f'{isotope[:2]}p' # Pap or Thp

    isotope_d_df = pd.read_csv(f"{validation_data_path}/{isotope_name_d}_df.csv")
    isotope_p_df = pd.read_csv(f"{validation_data_path}/{isotope_name_p}_df.csv")
    isotope_df = isotope_d_df

    mae_sim_dic: dict[str, dict[str, float]] = {isotope: {}}
    param_ref_dic: dict[str, dict[str, float]] = {}
    ratio_dic: dict[str, dict[str, float]] = {}

    def conv_dpm_bq(data: xr.Dataset, var: str) -> xr.DataArray:
        """
        Convert data from dpm to Bq.

        Parameters:
        data (xarray.Dataset): Dataset containing the data.
        var (str): Variable name to convert.

        Returns:
        xarray.DataArray: Converted data.
        """
        return data[var] * 10 ** 6 / (60 * data[["rho_SI"]]).rename({"rho_SI": var})[var]


    def extract_pad_value(row: pd.Series, var_model: xr.DataArray) -> float:
        """
        Extract the value for Pad from the model.

        Parameters:
        row (pd.Series): Row containing indices.
        var_model (xarray.DataArray): Model data array.

        Returns:
        float: Extracted value.
        """
        lon_idx = int(row['lon'])
        lat_idx = int(row['lat'])
        zt_idx = int(row['zt'])
        return var_model.isel(lon_t=lon_idx, lat_t=lat_idx, z_t=zt_idx).item()

    def path_mae(parameter_list: list[str], sim: str) -> None:
        """
        Calculate the mean absolute error for a given simulation.

        Parameters:
        parameter_list (list): List of parameters to calculate.
        sim (str): Simulation name.

        Returns:
        None
        """
        logging.info("Processing simulation: %s, Isotope: %s", sim, isotope)

        param_ref_dic[sim] = {}

        loladf = pd.DataFrame({
            "lon": isotope_df['Longitude'].apply(lambda x: find_nearest(model_xr[sim].lon_t, x)),
            "lat": isotope_df['Latitude'].apply(lambda x: find_nearest(model_xr[sim].lat_t, x)),
            "zt": isotope_df['DEPTH [m]'].apply(lambda x: find_nearest(model_xr[sim].z_t, x))
        })

        proxycop = model_xr[sim].isel(time=-1)
        var_model = conv_dpm_bq(proxycop, isotope)
        isotope_df[f'{isotope}_bern3d'] = loladf.apply(lambda row: extract_pad_value(row, var_model), axis=1)

        abs_err = abs(isotope_df[f"{isotope}_obs"] - isotope_df[f"{isotope}_bern3d"])
        weight_err = abs_err / isotope_df[f"{isotope}_std"]
        mae_sim_dic[isotope][sim] = (weight_err.sum()) / ((1 / isotope_df[f"{isotope}_std"]).sum())
        logging.info("MAE for %s", sim)

        for param in parameter_list:
            try:
                param_ref_dic[sim][param] = float(model_xr[sim][f"param_bgc_{param}"].values)
            except KeyError:
                logging.error("Parameter %s not found in simulation %s", param, sim)

        ratio_dic[sim] = {
                f"{isotope_name_p}/{isotope_name_d}": float((model_xr[sim][isotope_name_p] / model_xr[sim][isotope_name_d]).mean()),
            }
    logging.info("Starting parallel processing of simulations")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(lambda sim: path_mae(parameter_list, sim), sims)
    logging.info("Completed parallel processing of simulations")

    mae_df = pd.DataFrame(mae_sim_dic)
    param_df = pd.DataFrame.from_dict(param_ref_dic, orient="index")

    param_df[f"mae_{isotope_name_d.lower()}"] = param_df.index.map(mae_df[isotope_name_d])
    param_df[f"{isotope_name_p}/{isotope_name_d}_bern"] = param_df.index.map(pd.DataFrame(ratio_dic).T[f"{isotope_name_p}/{isotope_name_d}"])
    paratio_geotraces = isotope_p_df[f"{isotope_name_p}_obs"].mean() / isotope_d_df[f"{isotope_name_d}_obs"].mean()
    param_df[f"{isotope[:2]}ratiodiff"] = abs(param_df[f"{isotope_name_p}/{isotope_name_d}_bern"] - paratio_geotraces)

    return param_df

def compute_and_tell_optimizer(optimizer: Optimizer, isotope: str,
                               parameter_list: list[str],
                               simulation_dict: dict[str, xr.Dataset],
                               validation_data_path: str) -> tuple[pd.DataFrame, list]:
    """
    Compute the mean absolute error (MAE) and update the optimizer.

    Parameters:
    optimizer (Optimizer): Optimizer instance.
    isotope (str): Isotope type ("Pad" or "Thd").
    parameter_list (list): List of parameters to calculate.
    simulation_dict (dict): Dictionary of simulation datasets.
    validation_data_path (str): Path to the validation data.

    Returns:
    tuple: Dataframe with calculated parameters and score for all simulations and updated optimizer.
    """

    if not isinstance(parameter_list, list):
        parameter_list = [parameter_list]

    simulation_names = list(simulation_dict.keys())

    test_df = calculate_score_df(isotope, parameter_list, simulation_dict,
                                 simulation_names, validation_data_path)

    test_df.replace(0,1e6,inplace=True)
    test_df.replace(np.nan,1e6,inplace=True)
    tested_parameters = test_df[parameter_list].values.tolist()
    mae = test_df[f"mae_{isotope.lower()}"].values.tolist()
    optimizer.tell(tested_parameters, mae)
    logging.info("Told new parameters to optimizer")

    # Correct indeces to match only simulation names
    corrected_index = []
    for index in test_df.index:
        corrected_index.append(index.split("/")[-1].split(".")[0])

    test_df.index = corrected_index

    return test_df, optimizer
