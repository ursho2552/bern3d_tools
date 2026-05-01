"""
Module for defining scoring targets for Bayesian optimization in the BGC model context.
This includes both default targets (e.g., temperature and salinity) and a registry for
custom targets.
"""

import os
import logging

import pandas as pd
import xarray as xr
import numpy as np

from .protocols import ScoringTargetProtocol
from .base import ScoringTarget
from .utils import simulation_finished, nrmse, get_field_stability, get_config_value

class TargetRegistry:
    """Registry for default and custom scoring targets."""

    _targets: dict[str, type[ScoringTargetProtocol]] = {}

    @classmethod
    def register(cls, name: str, target_class: type[ScoringTargetProtocol]) -> None:
        """Register a target class."""
        cls._targets[name] = target_class

    @classmethod
    def get(cls, name: str) -> type[ScoringTargetProtocol]:
        """Get a registered target class."""
        if name not in cls._targets:
            raise ValueError(f"Target '{name}' not registered")
        return cls._targets[name]

    @classmethod
    def create(cls, name: str, **kwargs) -> ScoringTargetProtocol:
        """Create an instance of a target."""
        target_class = cls.get(name)
        return target_class(**kwargs)

class PhysicsTarget(ScoringTarget):
    """ Scoring target based on physical metrics. """

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score based on physical metrics.

        """

        # Get target value for amoc in case it is specified from kwargs
        target_amoc: float | None = kwargs.get("target_amoc", 15.5)
        variable_names_dict: dict[str, dict[str, str]] | None = kwargs.get("variable_names_dict", None)

        # Get validation data from file
        assert os.path.exists(validation_data_path), f"Validation data file not found: {validation_data_path}"
        ds_target = xr.open_dataset(validation_data_path)

        # Extract variables from validation data
        ds_temp_obs = ds_target[variable_names_dict["temp"]["obs"]].values
        ds_salt_obs = ds_target[variable_names_dict["salt"]["obs"]].values
        ds_ida_obs = ds_target[variable_names_dict["ida"]["obs"]].values

        # Extract variable names for model outputs
        sim_variable_name_temp: str = variable_names_dict["temp"]["sim"]
        sim_variable_name_salt: str = variable_names_dict["salt"]["sim"]
        sim_variable_name_ida: str = variable_names_dict["ida"]["sim"]

        # Prepare scores and parameter dictionaries
        composite_scores: dict[str, float] = {}
        param_ref_dic: dict[str, dict[str, float]] = {}

        for i, (sim, log_file, param_file) in enumerate(zip(sims, log_files, parameter_files)):

            if simulation_finished(log_file):
                # Set initial values for score components
                error_temp = 0.0
                error_salt = 0.0
                error_ida = 0.0
                error_amoc = 1.0

                stability_level_temp = 0.0
                stability_level_salt = 0.0
                stability_level_ida = 0.0

                ds_model: xr.Dataset = model_xr[sim]

                # Extract volume information and masks to compute weights
                cell_volume = ds_model["boxvol"].values
                mask_atlantic = ds_model["masks"].values == 1
                mask_pacific = ds_model["masks"].values == 2

                volume_atlantic = np.sum(cell_volume[mask_atlantic])
                volume_pacific = np.sum(cell_volume[mask_pacific])

                # Shrink weight of Pacific to match the Atlantic
                scale = np.ones_like(cell_volume)
                scale[mask_pacific] = volume_atlantic / volume_pacific

                weight = scale*cell_volume/np.nansum(scale*cell_volume)

                # Caculate the errors given the user input
                if "temp" in self.name:
                    ds_simulation = ds_model[sim_variable_name_temp].isel(time=-1).values
                    error_temp = nrmse(ds_simulation, ds_temp_obs, weight)

                    stability_level_temp = get_field_stability(ds=ds_model,
                                                               var_name=sim_variable_name_temp,
                                                               depth_level=0, window=10,
                                                               time_dim="time")

                if "salt" in self.name:
                    ds_simulation = ds_model[sim_variable_name_salt].isel(time=-1).values
                    error_salt = nrmse(ds_simulation, ds_salt_obs, weight)

                    stability_level_salt = get_field_stability(ds=ds_model,
                                                               var_name=sim_variable_name_salt,
                                                               depth_level=0, window=10,
                                                               time_dim="time")

                if "ida" in self.name:
                    ds_simulation = ds_model[sim_variable_name_ida].isel(time=-1).values
                    error_ida = nrmse(ds_simulation, ds_ida_obs, weight)

                    stability_level_ida = get_field_stability(ds=ds_model,
                                                              var_name=sim_variable_name_ida,
                                                              depth_level=20, window=10,
                                                              time_dim="time")

                if "amoc" in self.name:
                    target_amoc_min = target_amoc - 0.5
                    target_amoc_max = target_amoc + 0.5
                    # Get AMOC timeseries from model output (TODO uhe 01/05/2026: this is currently hardcoded and should be made more flexible)
                    sim_amoc = sim.replace("_full_ave.nc", "_timeseries_ave.nc")
                    ds_amoc = xr.open_dataset(sim_amoc, decode_times=False)

                    error_amoc = (abs(sim_amoc - target_amoc)/target_amoc if sim_amoc < target_amoc_min or sim_amoc > target_amoc_max else 0.0)

                # Combine errors into a composite score
                active_errors = error_temp + error_salt + error_ida + error_amoc
                active_stability = stability_level_temp + stability_level_salt + stability_level_ida

                # Combined error: sum of active errors, amplified by stability issues
                base_error = active_errors if active_errors else 0.0
                stability_multiplier = 1.0 + active_stability
                total_error = base_error*stability_multiplier

                # Edge case
                if total_error == 0.0 and active_stability:
                    total_error = stability_multiplier

                total_error = 1e6 if total_error > 10 else total_error

                composite_scores[sim] = total_error

            else:
                composite_scores[sim] = 1e6  # Assign a high error score if simulation is not finished
                logging.warning(f"Simulation '{sim}' is not finished. Assigned high error score.")

            param_ref_dic[sim] = {}
            for param in parameter_list:
                param_ref_dic[sim][param] = get_config_value(param_file, param)

        return self._prepare_dataframe(composite_scores, param_ref_dic)

class NPZDTarget(ScoringTarget):
    """ Scoring target based on NPZD metrics. """

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score based on NPZD metrics.

        This method should be implemented to compute the score based on the specific NPZD metric.
        """
        # Placeholder implementation
        scores = [0.0] * len(parameter_list)  # Dummy scores for demonstration
        params = {param: {} for param in parameter_list}  # Dummy parameters for demonstration

        return self._prepare_dataframe(scores, params)

class IsotopeTarget(ScoringTarget):
    """ Scoring target based on isotope metrics. """

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score based on isotope metrics.

        This method should be implemented to compute the score based on the specific isotope metric.
        """
        # Placeholder implementation
        scores = [0.0] * len(parameter_list)  # Dummy scores for demonstration
        params = {param: {} for param in parameter_list}  # Dummy parameters for demonstration

        return self._prepare_dataframe(scores, params)

# Register default targets
TargetRegistry.register("temp_salt_ida_amoc", PhysicsTarget)
TargetRegistry.register("npzd", NPZDTarget)
TargetRegistry.register("isotope", IsotopeTarget)
