#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Custom scoring targets for Bayesian optimization.

Register your custom targets here so they're available in both
main.py and postprocessing.py.
"""

import os
import logging

import numpy as np
import pandas as pd
import xarray as xr

from bayesian_optimization.scoring.base import ScoringTarget
from bayesian_optimization.scoring.targets import TargetRegistry
from bayesian_optimization.scoring.utils import (
    simulation_finished,
    nrmse,
    get_config_value
)

class MyCustomTarget(ScoringTarget):
    """Custom scoring target."""

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """Compute scores for nitrogen isotope target."""

        assert os.path.exists(validation_data_path), \
            f"Validation data path {validation_data_path} does not exist."

        ds_obs = pd.read_table(validation_data_path)
        base_obs = ds_obs[["Longitude", "Latitude", "Depth", "d15N"]].copy()
        base_obs = base_obs.replace([np.inf, -np.inf], np.nan).dropna(
            subset=["Longitude", "Latitude", "Depth", "d15N"]
        )

        composite_scores: dict[str, float] = {}
        param_ref_dic: dict[str, dict[str, float]] = {}

        for sim, log_file, param_file in zip(sims, log_files, parameter_files):
            if simulation_finished(log_file):
                ds_last = model_xr[sim].isel(time=-1)

                if "DINdel15" not in ds_last:
                    raise KeyError(
                        f"Model variable 'DINdel15' not found in simulation '{sim}'. "
                        f"Available variables: {list(ds_last.data_vars)}"
                    )

                da_model = ds_last["DINdel15"]

                # Create observation points dataset
                obs_points = xr.Dataset({
                    "lon_t": ("obs", base_obs["Longitude"].to_numpy()),
                    "lat_t": ("obs", base_obs["Latitude"].to_numpy()),
                    "z_t": ("obs", base_obs["Depth"].to_numpy()),
                })

                # Interpolate model to observation points
                sim_interp = da_model.interp(
                    lon_t=obs_points["lon_t"],
                    lat_t=obs_points["lat_t"],
                    z_t=obs_points["z_t"],
                    method="linear"
                )

                # Fill NaN values with nearest neighbor
                if np.any(np.isnan(sim_interp.values)):
                    sim_interp_nearest = da_model.interp(
                        lon_t=obs_points["lon_t"],
                        lat_t=obs_points["lat_t"],
                        z_t=obs_points["z_t"],
                        method="nearest"
                    )
                    sim_interp = sim_interp.fillna(sim_interp_nearest)

                # Compute weighted NRMSE
                sim_values = sim_interp.values
                obs_values = base_obs["d15N"].to_numpy()
                valid = ~np.isnan(sim_values) & ~np.isnan(obs_values)
                weights = np.abs(obs_values - 5) + 1  # Weight by difference to 5‰

                total_error = nrmse(
                    sim_values[valid],
                    obs_values[valid],
                    weights=weights[valid]
                )

                composite_scores[sim] = float(total_error)
                logging.info("N-isotope NRMSE: %.4f for simulation %s", total_error, sim)
            else:
                composite_scores[sim] = 1e6
                logging.warning("Simulation %s not finished. Setting score to 1e6.", sim)

            # Extract parameters
            param_ref_dic[sim] = {
                param: get_config_value(param_file, param)
                for param in parameter_list
            }

        return self._prepare_dataframe(composite_scores, param_ref_dic)


# Register Custom Targets
def register_custom_targets():
    """Register all custom targets with the TargetRegistry."""
    TargetRegistry.register(
        "nisotope",
        MyCustomTarget,
        aliases=["custom"]
    )
    logging.info("Registered custom target")

# Auto-register when imported
register_custom_targets()
