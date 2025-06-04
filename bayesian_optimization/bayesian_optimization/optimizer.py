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

def score_isotope(isotope: str, parameter_list: list[str],
                  model_xr: dict[str, xr.Dataset], sims: list[str],
                  validation_data_path: str,
                  parameter_files: list[str]) -> pd.DataFrame:

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


    logging.info("Starting processing of simulations")
    for i, sim in enumerate(sims):

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
            param_ref_dic[sim][param] = get_config_value(parameter_files[i], param)

        ratio_dic[sim] = {
                f"{isotope_name_p}/{isotope_name_d}": float((model_xr[sim][isotope_name_p] / model_xr[sim][isotope_name_d]).mean()),
            }

    mae_df = pd.DataFrame(mae_sim_dic)
    param_df = pd.DataFrame.from_dict(param_ref_dic, orient="index")

    param_df[f"mae_{isotope_name_d.lower()}"] = param_df.index.map(mae_df[isotope_name_d])
    param_df[f"{isotope_name_p}/{isotope_name_d}_bern"] = param_df.index.map(pd.DataFrame(ratio_dic).T[f"{isotope_name_p}/{isotope_name_d}"])
    paratio_geotraces = isotope_p_df[f"{isotope_name_p}_obs"].mean() / isotope_d_df[f"{isotope_name_d}_obs"].mean()
    param_df[f"{isotope[:2]}ratiodiff"] = abs(param_df[f"{isotope_name_p}/{isotope_name_d}_bern"] - paratio_geotraces)

    return param_df


def score_temperature_salinity(target: str, parameter_list: list[str],
                               model_xr: dict[str, xr.Dataset], sims: list[str],
                               validation_data_path: str,
                               parameter_files: list[str],
                               log_files: list[str],
                               target_amoc: float = None) -> pd.DataFrame:

    # The observations of temperature and salinity are already gridded on the model grid
    # and are stored in the run directory under the name world_68x46.observations.nc as the variable
    # "temp" and "salt" with dimensions (dept_t, lat_t, lon_t). Hence, the model output, can be
    # directly compared to the observations.

    # Open the NetCDF observations file and convert target variable to DataFrame
    target_file = f"{validation_data_path}/world_68x46.observations.nc"
    assert os.path.exists(target_file), f"{target_file} file does not exist."

    ds_target = xr.open_dataset(target_file)

    obs_df_temp = ds_target["temp"].to_dataframe().reset_index().dropna()
    obs_df_temp = obs_df_temp.rename(columns={"temp": "obs_temperature"})
    sim_variable_name_temp = "TEMP"
    obs_variable_name_temp = "obs_temperature"

    obs_df_salt = ds_target["salt"].to_dataframe().reset_index().dropna()
    obs_df_salt = obs_df_salt.rename(columns={"salt": "obs_salinity"})
    sim_variable_name_salt = "S"
    obs_variable_name_salt = "obs_salinity"

    # ensure target is a valid string
    assert target.lower() in ["temperature", "salinity", "temperature_salinity",
                              "salinity_temperature", "temp_salt", "salt_temp"], \
        f"Target must be either 'Temperature', 'Salinity', 'Temperature_Salinity', 'Salinity_Temperature', 'Temp_Salt' or 'Salt_Temp'."


    composite_scores: dict[str, float] = {}
    param_ref_dic: dict[str, dict[str, float]] = {}

    # Need to loop over the simulation names that have all, rahter than only those where it found a match in nc file
    # if sim is in the simulaiton names, get index --> i
    # else add a large value to the score, but still read in the paramters

    for i, sim in enumerate(sims):
        # Check if the simulation was successful
        if simulation_finished(log_files[i]):
            mae_temp = 0.0
            mae_salt = 0.0
            mae_amoc = 0.0

            model_ds = model_xr[sim].isel(time=-1)
            div_mae = 0
            # Calculate the MAE for temperature
            if 'temp' in target.lower():
                sim_df = model_ds[sim_variable_name_temp].to_dataframe().reset_index().dropna()
                sim_df = sim_df.rename(columns={sim_variable_name_temp: "sim_temperature", 'z_t': 'dep_t'})

                # Use merge to join on common coordinates
                merged = pd.merge(obs_df_temp, sim_df[['dep_t','lat_t','lon_t', "sim_temperature"]],
                                on=['dep_t','lat_t','lon_t'], how='inner')

                # Normalize the temperature values using the range of the observed values
                obs_min = merged[obs_variable_name_temp].min()
                obs_max = merged[obs_variable_name_temp].max()

                merged["sim_temperature"] = (merged["sim_temperature"] - obs_min)/(obs_max - obs_min)
                merged[obs_variable_name_temp] = (merged[obs_variable_name_temp] - obs_min)/(obs_max - obs_min)

                mae_temp = (merged["sim_temperature"] - merged[obs_variable_name_temp]).abs().mean()
                div_mae += 1

            # Calculate the MAE for salinity
            if 'salt' in target.lower():
                sim_df = model_ds[sim_variable_name_salt].to_dataframe().reset_index().dropna()
                sim_df = sim_df.rename(columns={sim_variable_name_salt: "sim_salinity", 'z_t': 'dep_t'})

                # Use merge to join on common coordinates
                merged = pd.merge(obs_df_salt, sim_df[['dep_t','lat_t','lon_t', "sim_salinity"]],
                                on=['dep_t','lat_t','lon_t'], how='inner')

                # Normalize the temperature values using the range of the observed values
                obs_min = merged[obs_variable_name_salt].min()
                obs_max = merged[obs_variable_name_salt].max()

                merged["sim_salinity"] = (merged["sim_salinity"] - obs_min)/(obs_max - obs_min)
                merged[obs_variable_name_salt] = (merged[obs_variable_name_salt] - obs_min)/(obs_max - obs_min)

                mae_salt = (merged["sim_salinity"] - merged[obs_variable_name_salt]).abs().mean()
                div_mae += 1

            # Calculate difference in AMOC strength
            # sim is the .nc file Bay_wind_00_000.00001765_full_ave.nc for which we want to subsitute the _full_ave.nc for _timeseries_inst.nc
            if target_amoc is not None:
                amoc_sim = sim.replace("_full_ave.nc", "_timeseries_inst.nc")
                ds_amoc = xr.open_dataset(amoc_sim, decode_times=False)
                sim_amoc = ds_amoc['OPSIA_max'][-1].values
                mae_amoc = abs(sim_amoc - target_amoc) if sim_amoc < target_amoc else 0.0
                div_mae += 1

            composite_scores[sim] = (mae_temp + mae_salt + mae_amoc)

        else:
            # If the simulation is not finished, set the score to a large value
            composite_scores[sim] = 1e6
            logging.info(f"Simulation {sim} not finished. Setting score to 1e6.")

        param_ref_dic[sim] = {}
        for param in parameter_list:
            param_ref_dic[sim][param] = get_config_value(parameter_files[i], param)

    mae_df = pd.DataFrame({target: composite_scores})
    param_df = pd.DataFrame.from_dict(param_ref_dic, orient="index")
    param_df[f"mae_{target.lower()}"] = param_df.index.map(mae_df[target])

    return param_df

def calculate_score_df(target: str, parameter_list: list[str],
                       model_xr: dict[str, xr.Dataset], sims: list[str],
                       validation_data_path: str,
                       parameter_files: list[str],
                       log_files: list[str],
                       target_amoc: float = None) -> pd.DataFrame:
    """
    Calculate the parameter dataframe for a given target and multiple simulations.

    Parameters:
    target (str): Target type ("Pad", "Thd", "Temperature", "Salinity").
    parameter_list (list): List of parameters to calculate.
    model_xr (dict): Dictionary of model datasets.
    sims (list): List of simulation names.
    validation_data_path (str): Path to the validation data.
    parameter_files (list): list of paths to the parameter files.
    log_files (list): list of paths to the log files.

    Returns:
    pd.DataFrame: Dataframe with calculated parameters and score for all simulations.
    """

    if target in ["Pad", "Thd"]:
        param_df = score_isotope(parameter_list, model_xr, sims, validation_data_path,
                                 parameter_files, log_files)

    elif target.lower() in ["temperature", "salinity", "temperature_salinity",
                              "salinity_temperature", "temp_salt", "salt_temp"]:
        param_df = score_temperature_salinity(target, parameter_list, model_xr,
                                              sims, validation_data_path, parameter_files,
                                              log_files, target_amoc)
    else:
        raise ValueError("Target must be either 'Pad', 'Thd', 'Temperature', or 'Salinity'.")

    return param_df

def get_config_value(path: str, param: str):
    """
    Get the value of a parameter from a configuration file.

    Parameters:
    path (str): Path to the configuration file.
    param (str): Parameter name to retrieve.

    Returns:
    str or int or float: Value of the parameter.
    """

    with open(path, encoding='utf-8') as f:
        for line in f:
            # strip comments and whitespace
            line = line.split('#', 1)[0].strip()
            if not line or '=' not in line:
                continue

            key, raw = map(str.strip, line.split('=', 1))
            if key == param:
                # infer numeric vs. string
                if re.fullmatch(r'[+-]?\d+\.\d*([eE][+-]?\d+)?', raw):
                    return float(raw)
                if re.fullmatch(r'[+-]?\d+', raw):
                    return int(raw)
                return raw.strip('"').strip("'")
    raise KeyError(f"No parameter named {param!r} in {path!r}")

def simulation_finished(log_path: str) -> bool:
    """
    Returns True if 'SIMULATION COMPLETE' appears anywhere in the file.
    """
    needle = "SIMULATION COMPLETE"
    with open(log_path, 'r', encoding='utf-8') as my_file:
        for line in my_file:
            if needle in line:
                return True
    return False

def compute_and_tell_optimizer(optimizer: Optimizer, target: str,
                               parameter_list: list[str],
                               simulation_dict: dict[str, xr.Dataset],
                               validation_data_path: str,
                               parameter_file_template: str,
                               target_amoc: float = None) -> tuple[pd.DataFrame, list]:
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

    if not isinstance(parameter_list, list):
        parameter_list = [parameter_list]

    simulation_names = list(simulation_dict.keys())
    # construct the paramter file name
    # should be in the run directory of the simulation

    parameter_files = []
    log_files = []
    
    for sim in simulation_names:
        root_dir = Path(sim).parent.parent
        name_sim = Path(sim).name.split(".")[0]
        name_param = parameter_file_template.format(simulation_name_bern3d=name_sim)
        parameter_files.append(f"{root_dir}/run_{name_sim}/{name_param}")
        log_files.append(f"{root_dir}/run_{name_sim}/{name_sim}.out")

    test_df = calculate_score_df(target, parameter_list, simulation_dict, simulation_names,
                                 validation_data_path, parameter_files, log_files, target_amoc)

    # Add a soft-penalty for failed simulations
    mae_values = test_df[f"mae_{target.lower()}"].values
    mae_values = np.where(mae_values == 1e6, np.nan, mae_values)
    if sum(np.isnan(mae_values)) == len(mae_values):
        # If more than half of the simulations failed, set mean and std to 2.5
        # This is a soft-penalty, so that the optimizer can still work with the data
        # but it will not be able to find a good solution
        logging.info("Most simulations failed. Setting mean to 2.5.")
        mean_mae = 2.0

    else:
        mean_mae = 2*np.nanmean(mae_values)


    corrected_mae = np.where(test_df[f"mae_{target.lower()}"] == 1e6,
                                                mean_mae,
                                                test_df[f"mae_{target.lower()}"])

    corrected_mae = corrected_mae.tolist()

    tested_parameters = test_df[parameter_list].values.tolist()
    #mae = test_df[f"mae_{target.lower()}"].values.tolist()
    optimizer.tell(tested_parameters, corrected_mae)
    logging.info("Told new parameters to optimizer")

    # Correct indeces to match only simulation names
    corrected_index = []
    for index in test_df.index:
        corrected_index.append(index.split("/")[-1].split(".")[0])

    test_df.index = corrected_index

    return test_df, optimizer
