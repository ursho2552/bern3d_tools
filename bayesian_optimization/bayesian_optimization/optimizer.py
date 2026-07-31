#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the optimizer script for the Bayesian optimization module.
"""
import os

import re
import logging
from typing import Union, Optional

from pathlib import Path
import pandas as pd
import xarray as xr
import numpy as np
import numpy.typing as npt
from skopt import Optimizer

def find_nearest(array: npt.ArrayLike, value: float,
                 retval: Optional[int] = 1) -> Union[float, int, tuple[float, int]]:
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

def nrmse(predictions: npt.ArrayLike, targets: npt.ArrayLike,
          weights: Optional[npt.ArrayLike] = None) -> float:
    """
    Calculate the Normalized Root Mean Square Error (NRMSE) between predictions and targets.

    Parameters:
    predictions (np.array): Predicted values.
    targets (np.array): Target values.

    Returns:
    float: NRMSE value.
    """
    assert len(predictions) == len(targets), "Predictions and targets must have the same length."
    weights = 1 if weights is None else weights

    mse = np.nanmean(weights*(predictions - targets) ** 2)
    nrmse_value = np.sqrt(mse) / (np.nanmax(targets) - np.nanmin(targets))

    return nrmse_value

def get_field_stability(ds: xr.Dataset, var_name: str, depth_level: Optional[int] = 0,
                        window: Optional[int] = 11,
                        time_dim: Optional[str] = "time",
                        min_stable_fraction: Optional[float] = 0.2) -> float:
    """
    Calculate the stability level of a field in a dataset.

    Parameters:
    ds (xr.Dataset): Input dataset containing the variable
    var_name (str): Name of the variable to analyze
    depth_level (int): Depth level index to select (default: 0)
    window (int): Rolling window size (default: 10)
    time_dim (str): Name of the time dimension (default: "time")
    min_stable_fraction (float): Minimum fraction of total time that must be stable (default: 0.2)

    Returns:
    float: Stability threshold (0.005-1.0), where lower values indicate higher stability
    """
    # Ensure odd window size for symmetric rolling window
    window = window + 1 if window % 2 == 0 else window

    # Calculate rolling variance
    data = ds[var_name].isel(z_t=depth_level).mean(dim=("lat_t", "lon_t"))
    data_variance = data.rolling({time_dim: window}, center=True).var()

    # Remove NaN values at the beginning and end due to rolling window
    half_window = window // 2
    valid_slice = slice(half_window, -half_window if half_window > 0 else None)
    data_variance_clean = data_variance[valid_slice]

    # Calculate stability level
    threshold = np.arange(0.001, 1.0, 0.001)
    max_variance = np.nanmax(data_variance_clean)

    if max_variance == 0 or np.isnan(max_variance):
        return 1.0

    relative_variance = data_variance_clean / max_variance
    valid_mask = ~np.isnan(relative_variance)
    no_nan_variance = relative_variance[valid_mask]

    if len(no_nan_variance) == 0:
        return 1.0

    total_length = len(no_nan_variance)
    min_stable_length = int(total_length * min_stable_fraction)

    # Find the lowest threshold where there's a point after which all remaining points are below it
    # and the stable period is at least min_stable_fraction of total time (20% for now)
    for thr in threshold:
        below_threshold = no_nan_variance < thr
        if np.any(below_threshold):
            # Find the first point that goes below threshold
            first_below_idx = np.where(below_threshold)[0][0]
            # Check if all points from that index onwards are below threshold
            stable_length = total_length - first_below_idx
            if (np.all(no_nan_variance[first_below_idx:] < thr) and
                stable_length >= min_stable_length):
                return thr

    return 1.0

def score_isotope(tuning_target: str, parameter_list: list[str],
                  model_xr: dict[str, xr.Dataset], sims: list[str],
                  validation_data_path: str,
                  parameter_files: list[str]) -> pd.DataFrame:

    # This feels dangerous.
    pd.options.mode.copy_on_write = True

    # Need to avoid using hardcoded paths (leave for now).
    # An option would be to use a config file that stores this information for each run
    isotope_name_d = f'{tuning_target[:2]}d' # Pad or Thd
    isotope_name_p = f'{tuning_target[:2]}p' # Pap or Thp

    isotope_d_df = pd.read_csv(f"{validation_data_path}/{isotope_name_d}_df.csv")
    isotope_p_df = pd.read_csv(f"{validation_data_path}/{isotope_name_p}_df.csv")
    isotope_df = isotope_d_df

    mae_sim_dic: dict[str, dict[str, float]] = {tuning_target: {}}
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
        var_model = conv_dpm_bq(proxycop, tuning_target)
        isotope_df[f'{tuning_target}_bern3d'] = loladf.apply(lambda row: extract_pad_value(row, var_model), axis=1)

        abs_err = abs(isotope_df[f"{tuning_target}_obs"] - isotope_df[f"{tuning_target}_bern3d"])
        weight_err = abs_err / isotope_df[f"{tuning_target}_std"]
        mae_sim_dic[tuning_target][sim] = (weight_err.sum()) / ((1 / isotope_df[f"{tuning_target}_std"]).sum())
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
    param_df[f"{tuning_target[:2]}ratiodiff"] = abs(param_df[f"{isotope_name_p}/{isotope_name_d}_bern"] - paratio_geotraces)

    return param_df


def score_temp_salt_amoc_ida(target: str, parameter_list: list[str],
                             model_xr: dict[str, xr.Dataset], sims: list[str],
                             validation_data_path: str,
                             parameter_files: list[str],
                             log_files: list[str], **kwargs: float) -> pd.DataFrame:


    # The observations of temperature and salinity are already gridded on the model grid
    # and are stored in the run directory under the name world_68x46.observations.nc as the variable
    # "temp" and "salt" with dimensions (dept_t, lat_t, lon_t). Hence, the model output, can be
    # directly compared to the observations.

    # get target values from kwargs
    target_amoc = kwargs.get('target_amoc', None)

    variable_names_dict = kwargs.get('variable_names', None)

    # Open the NetCDF observations file and convert target variable to DataFrame
    target_file = f"{validation_data_path}/world_68x46.observations.nc"
    assert os.path.exists(target_file), f"{target_file} file does not exist."

    ds_target = xr.open_dataset(target_file)

    obs_df_temp = ds_target[variable_names_dict["temp"]["obs"]].values
    sim_variable_name_temp = variable_names_dict["temp"]["sim"]

    obs_df_salt = ds_target[variable_names_dict["salt"]["obs"]].values
    sim_variable_name_salt = variable_names_dict["salt"]["sim"]

    obs_df_ida = ds_target[variable_names_dict["ida"]["obs"]].values
    sim_variable_name_ida = variable_names_dict["ida"]["sim"]

    composite_scores: dict[str, float] = {}
    param_ref_dic: dict[str, dict[str, float]] = {}

    for i, sim in enumerate(sims):
        # Check if the simulation was successful

        if simulation_finished(log_files[i]):
            error_temp = 0.0
            error_salt = 0.0
            error_amoc = 1.0
            error_ida = 0.0

            stability_level_temp = 0.0
            stability_level_salt = 0.0
            stability_level_ida = 0.0

            model_ds = model_xr[sim].isel(time=-1)
            model_ds_full = model_xr[sim]
            # Get weights for the model grid
            cell_volume = model_ds.boxvol.values
            mask_atl = model_ds.masks.values == 1
            mask_pac = model_ds.masks.values == 3
            # Calculate the volume of the Atlantic and Pacific Ocean
            vol_atl = np.nansum(cell_volume[mask_atl])
            vol_pac = np.nansum(cell_volume[mask_pac])

            # Schrink Pacific to match Atlantic; Atlantic = 1; others = 1
            scale = np.ones_like(cell_volume)
            scale[mask_pac] = vol_atl / vol_pac
            scale[mask_atl] = 1.0

            # incorporate physical volume
            raw_w = scale * cell_volume
            weight = raw_w / np.nansum(raw_w)

            # Calculate the MAE for temperature
            if 'temp' in target.lower():
                sim_df = model_ds[sim_variable_name_temp].values
                error_temp = nrmse(sim_df, obs_df_temp, weight)

                stability_level_temp = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_temp,
                                                        depth_level=0, window=10,
                                                        time_dim="time")

            # Calculate the MAE for salinity
            if 'salt' in target.lower():
                sim_df = model_ds[sim_variable_name_salt].values
                error_salt = nrmse(sim_df, obs_df_salt, weight)

                stability_level_salt = get_field_stability(ds=model_ds_full,
                                                            var_name=sim_variable_name_salt,
                                                            depth_level=0, window=10,
                                                            time_dim="time")

            # Calcualte difference in ideal age
            # ideal age is stored in the model output as ida and in the observations_ida.nc file as "ida"
            if 'ida' in target.lower():
                sim_df = model_ds[sim_variable_name_ida].values
                error_ida = nrmse(sim_df, obs_df_ida, weight)

                stability_level_ida = get_field_stability(ds=model_ds_full,
                                                            var_name=sim_variable_name_ida,
                                                            depth_level=20, window=10,
                                                            time_dim="time")

            # Calculate difference in AMOC strength
            if target_amoc is None:
                target_amoc = 15.5
            target_amoc_min = target_amoc - 0.5
            target_amoc_max = target_amoc + 0.5

            if 'amoc' in target.lower():
                amoc_sim = sim.replace("_full_ave.nc", "_timeseries_ave.nc")
                ds_amoc = xr.open_dataset(amoc_sim, decode_times=False)
                sim_amoc = ds_amoc[variable_names_dict["amoc"]["sim"]][-1].values
                error_amoc = (abs(sim_amoc - target_amoc)/target_amoc if sim_amoc < target_amoc_min or sim_amoc > target_amoc_max else 0.0)

            # Combine errors. If temperature, salinity and ideal age are perfect or not used,
            # then the total error is just the AMOC error. Else, the amoc error is used as a multiplier
            # for the other errors. Similarly, for the stability levels.
            main_error = error_temp + error_salt + error_ida
            stability_error = 1 + stability_level_temp + stability_level_salt + stability_level_ida

            if main_error == 0:
                total_error = stability_error*error_amoc if error_amoc > 0 else stability_error
            else:
                total_error = (stability_error*main_error) + error_amoc

            logging.info(f"Total error is {total_error} for simulation {sim}")
            logging.info(f"error_temp: {error_temp}, error_salt: {error_salt}, error_ida: {error_ida}, error_amoc: {error_amoc}")
            logging.info(f"stability_level_temp: {stability_level_temp}, stability_level_salt: {stability_level_salt}, stability_level_ida: {stability_level_ida}")

            if total_error > 10:
                total_error = 1e6
            elif total_error < 0:
                total_error = 1e6

            composite_scores[sim] = total_error

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

def score_npzd(target: str, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
               sims: list[str], validation_data_path: str, parameter_files: list[str],
               log_files: list[str], **kwargs: float) -> pd.DataFrame:

    # get target values from kwargs
    target_poc = kwargs.get('target_poc', None)
    target_caco3 = kwargs.get('target_caco3', None)
    target_opal = kwargs.get('target_opal', None)
    target_npp = kwargs.get('target_npp', None)

    variable_names_dict = kwargs.get('variable_names', None)

    # Here, we score the NPZD model output against observed DIC, PO4, NO3, and the overall NPP and
    # POC, opal, and CaCO3 export at 120 m depth.

    # Open the NetCDF observations file and convert target variable to DataFrame
    target_file = f"{validation_data_path}/world_68x46.observations.nc"
    assert os.path.exists(target_file), f"{target_file} file does not exist."

    ds_target = xr.open_dataset(target_file, decode_times=False)

    obs_df_dic = ds_target[variable_names_dict["dic"]["obs"]].values
    sim_variable_name_dic = variable_names_dict["dic"]["sim"]

    obs_df_alk = ds_target[variable_names_dict["alk"]["obs"]].values
    sim_variable_name_alk = variable_names_dict["alk"]["sim"]

    obs_df_po4 = ds_target[variable_names_dict["po4"]["obs"]].values
    sim_variable_name_po4 = variable_names_dict["po4"]["sim"]

    obs_df_sio = ds_target[variable_names_dict["sio"]["obs"]].values
    sim_variable_name_sio = variable_names_dict["sio"]["sim"]

    obs_df_no3 = ds_target[variable_names_dict["no3"]["obs"]].values
    sim_variable_name_no3 = variable_names_dict["no3"]["sim"]

    # Can have dic, alk, po4, poc, caco3, opal, npp
    composite_scores: dict[str, float] = {}
    param_ref_dic: dict[str, dict[str, float]] = {}

    for i, sim in enumerate(sims):
        # Check if the simulation was successful
        if simulation_finished(log_files[i]):
            error_dic = 0.0
            error_alk = 0.0
            error_po4 = 0.0
            error_sio = 0.0
            error_no3 = 0.0
            error_poc = 0.0
            error_caco3 = 0.0
            error_opal = 0.0
            error_npp = 0.0

            stability_level_dic = 0.0
            stability_level_alk = 0.0
            stability_level_po4 = 0.0
            stability_level_sio = 0.0
            stability_level_no3 = 0.0

            model_ds = model_xr[sim].isel(time=-1)
            model_ds_full = model_xr[sim]
            # Get weights for the model grid
            area = model_ds.area.values

            # Calculate the MAE for targets
            if 'dic' in target.lower():
                sim_df = model_ds[sim_variable_name_dic].values * 1000
                error_dic = nrmse(sim_df, obs_df_dic, 1)
                stability_level_dic = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_dic,
                                                        depth_level=0, window=10,
                                                        time_dim="time")
            if 'alk' in target.lower():
                sim_df = model_ds[sim_variable_name_alk].values * 1000
                error_alk = nrmse(sim_df, obs_df_alk, 1)
                stability_level_alk = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_alk,
                                                        depth_level=0, window=10,
                                                        time_dim="time")
            if 'po4' in target.lower():
                sim_df = model_ds[sim_variable_name_po4].values * 1000
                error_po4 = nrmse(sim_df, obs_df_po4, 1)
                stability_level_po4 = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_po4,
                                                        depth_level=0, window=10,
                                                        time_dim="time")
            if 'sio' in target.lower():
                sim_df = model_ds[sim_variable_name_sio].values * 1000
                error_sio = nrmse(sim_df, obs_df_sio, 1)
                stability_level_sio = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_sio,
                                                        depth_level=0, window=10,
                                                        time_dim="time")
            if 'no3' in target.lower():
                sim_df = model_ds[sim_variable_name_no3].values * 1000
                error_no3 = nrmse(sim_df, obs_df_no3, 1)
                stability_level_no3 = get_field_stability(ds=model_ds_full,
                                                        var_name=sim_variable_name_no3,
                                                        depth_level=0, window=10,
                                                        time_dim="time")

            # Calculate difference in export value, pools, and NPP
            if target_poc is None:
                target_poc = 9.7
            target_poc_min = target_poc - 0.25
            target_poc_max = target_poc + 0.25

            if target_caco3 is None:
                target_caco3 = 1.9
            target_caco3_min = target_caco3 - 0.3
            target_caco3_max = target_caco3 + 0.3

            if target_opal is None:
                target_opal = 190
            target_opal_min = target_opal - 52
            target_opal_max = target_opal + 52

            if target_npp is None:
                target_npp = 60
            target_npp_min = target_npp - 17
            target_npp_max = target_npp + 17

            # Should all be in the same file as the previous
            factor_C = 12.01  # g C per mol C
            nsecyr = 365*24*60*60  # seconds per year
            if 'npp' in target.lower():
                # Get the NPP and multiply with area 12.01 and nsecyr to get total NPP
                sim_df = np.nansum(model_ds[variable_names_dict["npp"]["sim"]].values*area*factor_C*nsecyr)/1e15  # in Pg C yr-1
                error_npp = (abs(sim_df - target_npp)/target_npp if sim_df < target_npp_min or sim_df > target_npp_max else 0.0)
            if 'poc' in target.lower():
                sim_df = np.nansum(model_ds[variable_names_dict["poc"]["sim"]].values*area*factor_C*nsecyr)/1e15  # in Pg C yr-1
                error_poc = (abs(sim_df - target_poc)/target_poc if sim_df < target_poc_min or sim_df > target_poc_max else 0.0)
            if 'caco3' in target.lower():
                sim_df = np.nansum(model_ds[variable_names_dict["caco3"]["sim"]].values*area*factor_C*nsecyr)/1e15 # in Pg C yr-1
                error_caco3 = (abs(sim_df - target_caco3)/target_caco3 if sim_df < target_caco3_min or sim_df > target_caco3_max else 0.0)
            if 'opal' in target.lower():
                sim_df = np.nansum(model_ds[variable_names_dict["opal"]["sim"]].values*area*nsecyr)/1e12 # in Tmol Si yr-1
                error_opal = (abs(sim_df - target_opal)/target_opal if sim_df < target_opal_min or sim_df > target_opal_max else 0.0)

            bulk_errors = 1 + error_npp + error_poc + error_caco3 + error_opal
            stability_error = 1 + stability_level_dic + stability_level_alk + stability_level_po4 + stability_level_sio + stability_level_no3

            # Combine errors. If dic, alk, po4, and sio are perfect or not used,
            # then the total error is just the export and NPP error. Else, the export and NPP error
            # are used as a multiplier for the other errors.
            main_error = error_dic + error_alk  + error_po4 + error_sio + error_no3
            if main_error == 0:
                total_error = stability_error*(bulk_errors - 1)
            else:
                total_error = stability_error*bulk_errors*main_error

            logging.info(f"Total error is {total_error} for simulation {sim}")
            logging.info (f"error_dic: {error_dic}, error_alk: {error_alk}, error_po4: {error_po4}, error_sio: {error_sio}, error_no3: {error_no3}")
            logging.info (f"error_npp: {error_npp}, error_poc: {error_poc}, error_caco3: {error_caco3}, error_opal: {error_opal}")
            logging.info (f"stability_level_dic: {stability_level_dic}, stability_level_alk: {stability_level_alk}, stability_level_po4: {stability_level_po4}, stability_level_sio: {stability_level_sio}, stability_level_no3: {stability_level_no3}")

            if total_error > 20:
                total_error = 1e6
            elif total_error < 0:
                total_error = 1e6

            composite_scores[sim] = total_error

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
                       **kwargs: float) -> pd.DataFrame:
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

    elif any(t in target.lower() for t in ["temp", "salt", 'amoc', 'ida']):
        param_df = score_temp_salt_amoc_ida(target, parameter_list, model_xr,
                                              sims, validation_data_path, parameter_files,
                                              log_files, **kwargs)

    # but it might be a combination of many targets with dic, alk, po4, sio, poc, caco3, opal, npp
    elif any(t in target.lower() for t in ["dic", "alk", "po4", "sio" , "no3", "poc", "caco3", "opal", "npp"]):
        param_df = score_npzd(target, parameter_list, model_xr,
                              sims, validation_data_path, parameter_files,
                              log_files, **kwargs)
    else:
        raise ValueError("Target must be the isotopes 'Pad' and/or 'Thd', the variables 'temp' and/or 'salt', or the variables 'dic', 'alk', 'po4', 'sio', 'poc', 'caco3', 'opal', 'npp'.")

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


def get_config_value(path: Union[str, list[str]], param: str):
    """
    Get the value of a parameter from a configuration file.

    Parameters:
    path (str or list[str]): Path to the configuration file.
    param (str): Parameter name to retrieve.

    Returns:
    str or int or float: Value of the parameter.
    """
    if not isinstance(path, list):
        path = [path]
    for path_item in path:
        with open(path_item, encoding='utf-8') as f:
            for line in f:
                line = line.split('#', 1)[0].strip()

                if line.startswith('[') and line.endswith(']'):
                    continue

                if not line or ("=" not in line and ":" not in line):
                    continue

                symbol = "=" if "=" in line else ":"

                if line.count(symbol) != 1:
                    continue

                key, raw = map(str.strip, line.split(symbol, 1))
                if key == param:
                    v = raw.strip()
                    if v.lower() in ('.true.', 'true'):
                        return True
                    if v.lower() in ('.false.', 'false'):
                        return False
                    if re.fullmatch(r'[+-]?\d+', v):
                        return int(v)
                    if re.fullmatch(r'[+-]?\d*\.?\d*[eE][+-]?\d+', v):
                        return float(v)
                    if re.fullmatch(r'[+-]?\d*\.\d*', v) and '.' in v:
                        return float(v)

                    return v.strip('"').strip("'")

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
