#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These are the utility functions used to regrid data to the Bern3D grid
"""

import xarray as xr
import xesmf as xe

def regrid_to_bern3d(ds_observation: xr.DataArray, variable: str,template_grid: xr.DataArray,
                     dim_dictionary: dict[str, str] = None,
                     bern3d_dimensions: dict[str, str] = {'depth': 'dep_t',
                                                          'lat': 'lat_t',
                                                          'lon': 'lon_t'}) -> xr.DataArray:
    """
    Regrid the observation data to the Bern3D grid using xesmf.

    Parameters:
    ds_observation (xr.DataArray): The observation data to regrid.
    variable (str): The variable name in the observation data to regrid.
    template_grid (xr.DataArray): The Bern3D grid to regrid to.
    dim_dictionary (dict[str, str], optional): A dictionary mapping the dimension names in the
        observation data to the standard names. Defaults to None.
    bern3d_dimensions (dict[str, str], optional): A dictionary mapping the standard dimension names
        to the Bern3D dimension names. Defaults to {'depth': 'dep_t', 'lat': 'lat_t', 'lon': 'lon_t'}.

    Returns:
    xr.DataArray: The regridded observation data.
    """

    # Rename variables if needed
    for key, value in dim_dictionary.items():
        if not key in ds_observation[variable].squeeze().dims:
            ds_observation = ds_observation.rename({value: key})

    depth_grid = template_grid[bern3d_dimensions['depth']].values

    # Start vertical interpolation
    original_variable = ds_observation[variable].squeeze()
    ds_vert_interp = original_variable[:,:,:].interp(
        depth=depth_grid, method='linear')

    # Ensure sequence of dimensions is correct
    ds_in = ds_vert_interp.copy()
    ds_in = ds_in.transpose(..., "lat", "lon")

    # Define output Dataset
    ds_out = xr.Dataset(
        {
            "lat": (["lat"], template_grid[bern3d_dimensions['lat']].values, {"units": "degrees_north"}),
            "lon": (["lon"], template_grid[bern3d_dimensions['lon']].values, {"units": "degrees_east"}),
        }
    )

    # Define regridder and return regridded values
    regridder = xe.Regridder(ds_in, ds_out, "bilinear")
    ds_regridded = regridder(ds_in)

    # rename dimensions back to bern3d
    for key, value in bern3d_dimensions.items():
        ds_regridded = ds_regridded.rename({key: value})

    return ds_regridded

def clean_encodings(ds: xr.DataArray, valid_keys: dict[str, str]):
    """
    Clean the encodings of a xarray DataArray to only include valid keys.

    Parameters:
    ds (xr.DataArray): The DataArray to clean.
    valid_keys (dict[str, str]): A dictionary of valid encoding keys.

    Returns:
    dict: A dictionary of cleaned encodings.
    """

    encoding: dict[str, str] = {}
    for var in ds.data_vars:
        encoding[var] = {
            k: v for k, v in ds[var].encoding.items()
            if k in valid_keys
        }
    return encoding
