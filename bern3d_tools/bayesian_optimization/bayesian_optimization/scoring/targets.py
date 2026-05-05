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
from .utils import simulation_finished, nrmse, get_field_stability, get_config_value, find_nearest

class TargetRegistry:
    """Registry for default and custom scoring targets."""

    _targets: dict[str, type[ScoringTargetProtocol]] = {}
    _aliases: dict[str, str] = {}

    @classmethod
    def register(cls, name: str, target_class: type[ScoringTargetProtocol],
                 aliases: list[str] | None = None) -> None:
        """Register a target class."""
        cls._targets[name] = target_class
        cls._aliases[name] = name

        if aliases:
            for alias in aliases:
                cls._aliases[alias.lower()] = name

    @classmethod
    def get(cls, name: str) -> type[ScoringTargetProtocol]:
        """Get a registered target class by checking if any alias appears in name."""
        name_lower = name.lower()

        # Check if alias appears in the target string
        matches = {}  # canonical_name -> list of matching aliases
        for alias, canonical_name in cls._aliases.items():
            if alias in name_lower:
                if canonical_name not in matches:
                    matches[canonical_name] = []
                matches[canonical_name].append(alias)

        if len(matches) == 0:
            raise ValueError(
                f"Target '{name}' not registered. No alias found in target string. "
                f"Available aliases: {sorted(set(cls._aliases.keys()))}"
            )
        elif len(matches) > 1:
            raise ValueError(
                f"Target '{name}' is ambiguous - matches multiple classes: {list(matches.keys())}. "
                f"Matching aliases: {matches}"
            )

        # Single match found
        canonical_name = list(matches.keys())[0]
        return cls._targets[canonical_name]

    @classmethod
    def create(cls, registry_name: str, **kwargs) -> ScoringTargetProtocol:
        """Create an instance of a target."""
        target_class = cls.get(registry_name)
        return target_class(**kwargs)

    @classmethod
    def list_targets(cls) -> list[str]:
        """List all registered canonical target names.

        Returns:
            Sorted list of canonical target names.
        """
        return sorted(cls._targets.keys())

    @classmethod
    def list_all_aliases(cls) -> list[str]:
        """List all registered aliases (including canonical names).

        Returns:
            Sorted list of all aliases.
        """
        return sorted(set(cls._aliases.keys()))

    @classmethod
    def is_valid_target(cls, name: str) -> bool:
        """Check if a target name contains any registered alias.

        Args:
            name: Target name to check

        Returns:
            True if name contains a registered alias, False otherwise.
        """
        name_lower = name.lower()
        return any(alias in name_lower for alias in cls._aliases.keys())

class PhysicsTarget(ScoringTarget):
    """ Scoring target based on physical metrics. """

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score based on physical metrics.

            This method computes a composite score based on the errors in temperature, salinity,
            IDA, and AMOC metrics, as well as their stability levels. The score is designed to
            penalize both large errors and instability in the model outputs compared to the
            validation data. The method also checks if the simulation has finished before computing
            the score, assigning a high error score if it has not.

            Args:
                parameter_list: List of parameter set names.
                model_xr: Dictionary of xarray Datasets for each simulation.
                sims: List of simulation names corresponding to the model_xr keys.
                validation_data_path: Path to the validation data file.
                parameter_files: List of file paths for the parameter sets.
                log_files: List of file paths for the simulation logs.
                **kwargs: Additional keyword arguments for scoring, such as target AMOC value and
                    variable names.

            Returns:
                DataFrame with parameters and their corresponding composite scores.

        """

        # Get target value for amoc in case it is specified from kwargs
        target_amoc: float = kwargs.get("target_amoc", 15.5)
        variable_names_dict: dict[str, dict[str, str]] | None = kwargs.get("variable_names", None)

        # Get validation data from file
        assert os.path.exists(validation_data_path), (f"Validation data file not found: "
                                                      f"{validation_data_path}")
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

        for sim, log_file, param_file in zip(sims, log_files, parameter_files):

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
                    file_amoc = sim.replace("_full_ave.nc", "_timeseries_ave.nc")
                    ds_amoc = xr.open_dataset(file_amoc, decode_times=False)
                    sim_amoc = ds_amoc[variable_names_dict["amoc"]["sim"]][-1].values

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
                # Assign a high error score if simulation is not finished
                composite_scores[sim] = 1e6
                logging.warning("Simulation '%s' is not finished. Assigned high error score.", sim)

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

            This method computes a composite score based on the errors in DIC, alkalinity,
            phosphate, silicate, nitrate, as well as errors in export production (POC, CaCO3, opal)
            and NPP, and their stability levels. The score is designed to penalize both large errors
            and instability in the model outputs compared to the validation data. The method also
            checks if the simulation has finished before computing the score, assigning a high error
            score if it has not.

            Args:
                parameter_list: List of parameter set names.
                model_xr: Dictionary of xarray Datasets for each simulation.
                sims: List of simulation names corresponding to the model_xr keys.
                validation_data_path: Path to the validation data file.
                parameter_files: List of file paths for the parameter sets.
                log_files: List of file paths for the simulation logs.
                **kwargs: Additional keyword arguments for scoring, such as target values for export
                    production and NPP, and variable names.

            Returns:
                DataFrame with parameters and their corresponding composite scores.

        """

        # Get target values from kwargs
        target_poc: float = kwargs.get("target_poc", 9.7)
        target_caco3: float = kwargs.get("target_caco3", 1.9)
        target_opal: float = kwargs.get("target_opal", 190.0)
        target_npp: float = kwargs.get("target_npp", 60.0)

        variable_names_dict: dict[str, dict[str, str]] | None = kwargs.get("variable_names", None)

        # Get validation data from file
        assert os.path.exists(validation_data_path), f"Validation data file not found: {validation_data_path}"
        ds_target = xr.open_dataset(validation_data_path)

        # Extract variables from validation data
        ds_dic_obs = ds_target[variable_names_dict["dic"]["obs"]].values
        ds_alk_obs = ds_target[variable_names_dict["alk"]["obs"]].values
        ds_po4_obs = ds_target[variable_names_dict["po4"]["obs"]].values
        ds_sio_obs = ds_target[variable_names_dict["sio"]["obs"]].values
        ds_no3_obs = ds_target[variable_names_dict["no3"]["obs"]].values

        # Extract variable names for model outputs
        sim_variable_name_dic: str = variable_names_dict["dic"]["sim"]
        sim_variable_name_alk: str = variable_names_dict["alk"]["sim"]
        sim_variable_name_po4: str = variable_names_dict["po4"]["sim"]
        sim_variable_name_sio: str = variable_names_dict["sio"]["sim"]
        sim_variable_name_no3: str = variable_names_dict["no3"]["sim"]

        # Prepare scores and parameter dictionaries
        composite_scores: dict[str, float] = {}
        param_ref_dic: dict[str, dict[str, float]] = {}

        for sim, log_file, param_file in zip(sims, log_files, parameter_files):

            if simulation_finished(log_file):
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

                ds_model = model_xr[sim]
                area = ds_model.area.values

                # Calculate the MAE for targets
                # TODO uhe 01/05/2026: This is very repetitive and could be refactored to be more
                # concise, but for now this is easier to compare with previous verison

                if 'dic' in self.name:
                    ds_sim = ds_model[sim_variable_name_dic].isel(time=-1).values * 1000
                    error_dic = nrmse(ds_sim, ds_dic_obs, 1)
                    stability_level_dic = get_field_stability(ds=ds_model,
                                                            var_name=sim_variable_name_dic,
                                                            depth_level=0, window=10,
                                                            time_dim="time")
                if 'alk' in self.name:
                    sim_df = ds_model[sim_variable_name_alk].isel(time=-1).values * 1000
                    error_alk = nrmse(sim_df, ds_alk_obs, 1)
                    stability_level_alk = get_field_stability(ds=ds_model,
                                                            var_name=sim_variable_name_alk,
                                                            depth_level=0, window=10,
                                                            time_dim="time")
                if 'po4' in self.name:
                    sim_df = ds_model[sim_variable_name_po4].isel(time=-1).values * 1000
                    error_po4 = nrmse(sim_df, ds_po4_obs, 1)
                    stability_level_po4 = get_field_stability(ds=ds_model,
                                                            var_name=sim_variable_name_po4,
                                                            depth_level=0, window=10,
                                                            time_dim="time")
                if 'sio' in self.name:
                    sim_df = ds_model[sim_variable_name_sio].isel(time=-1).values * 1000
                    error_sio = nrmse(sim_df, ds_sio_obs, 1)
                    stability_level_sio = get_field_stability(ds=ds_model,
                                                            var_name=sim_variable_name_sio,
                                                            depth_level=0, window=10,
                                                            time_dim="time")
                if 'no3' in self.name:
                    sim_df = ds_model[sim_variable_name_no3].isel(time=-1).values * 1000
                    error_no3 = nrmse(sim_df, ds_no3_obs, 1)
                    stability_level_no3 = get_field_stability(ds=ds_model,
                                                            var_name=sim_variable_name_no3,
                                                            depth_level=0, window=10,
                                                            time_dim="time")

                # Calculate difference in export value, pools, and NPP
                factor_C = 12.01  # g C per mol C
                nsecyr = 365*24*60*60  # seconds per year
                if 'npp' in self.name:
                    # Get the NPP and multiply with area 12.01 and nsecyr to get total NPP
                    target_npp_min = target_npp - 17
                    target_npp_max = target_npp + 17
                    sim_df = np.nansum(ds_model[variable_names_dict["npp"]["sim"]][-1].values*area*factor_C*nsecyr)/1e15  # in Pg C yr-1
                    error_npp = (abs(sim_df - target_npp)/target_npp if sim_df < target_npp_min or sim_df > target_npp_max else 0.0)

                if 'poc' in self.name:
                    target_poc_min = target_poc - 0.25
                    target_poc_max = target_poc + 0.25
                    sim_df = np.nansum(ds_model[variable_names_dict["poc"]["sim"]][-1].values*area*factor_C*nsecyr)/1e15  # in Pg C yr-1
                    error_poc = (abs(sim_df - target_poc)/target_poc if sim_df < target_poc_min or sim_df > target_poc_max else 0.0)

                if 'caco3' in self.name:
                    target_caco3_min = target_caco3 - 0.3
                    target_caco3_max = target_caco3 + 0.3
                    sim_df = np.nansum(ds_model[variable_names_dict["caco3"]["sim"]][-1].values*area*factor_C*nsecyr)/1e15 # in Pg C yr-1
                    error_caco3 = (abs(sim_df - target_caco3)/target_caco3 if sim_df < target_caco3_min or sim_df > target_caco3_max else 0.0)

                if 'opal' in self.name:
                    target_opal_min = target_opal - 52
                    target_opal_max = target_opal + 52
                    sim_df = np.nansum(ds_model[variable_names_dict["opal"]["sim"]][-1].values*area*nsecyr)/1e12 # in Tmol Si yr-1
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

                if total_error > 20:
                    total_error = 1e6
                elif total_error < 0:
                    total_error = 1e6

                composite_scores[sim] = total_error

            else:
                composite_scores[sim] = 1e6  # Assign a high error score if simulation is not finished
                logging.warning("Simulation '%s' is not finished. Assigned high error score.", sim)

            param_ref_dic[sim] = {}
            for param in parameter_list:
                param_ref_dic[sim][param] = get_config_value(param_file, param)

        return self._prepare_dataframe(composite_scores, param_ref_dic)

class IsotopeTarget(ScoringTarget):
    """ Scoring target based on isotope metrics. """

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score based on isotope metrics.

            This method computes a score based on the weighted mean absolute error (MAE) between the
            model outputs and the validation data for a specific isotope target. The score is
            designed to penalize large errors in the model outputs compared to the validation data,
            with weights based on the standard deviation of the observations. The method also checks
            if the simulation has finished before computing the score, assigning a high error score
            if it has not.

            Parameters:
                parameter_list: List of parameter set names.
                model_xr: Dictionary of xarray Datasets for each simulation.
                sims: List of simulation names corresponding to the model_xr keys.
                validation_data_path: Path to the validation data file.
                parameter_files: List of file paths for the parameter sets.
                log_files: List of file paths for the simulation logs.
                **kwargs: Additional keyword arguments for scoring, such as variable names.

            Returns:
                DataFrame with parameters and their corresponding scores.

        """

        df_isotope_obs = pd.read_csv(validation_data_path)
        composite_scores: dict[str, float] = {}
        param_ref_dic: dict[str, dict[str, float]] = {}

        for sim, log_file, param_file in zip(sims, log_files, parameter_files):

            if simulation_finished(log_file):
                composite_scores[sim] = self._compute_isotope_score(model_xr[sim], df_isotope_obs,
                                                                    self.name)
            else:
                composite_scores[sim] = 1e6  # Assign a high error score if simulation is not finished
                logging.warning(f"Simulation '{sim}' is not finished. Assigned high error score.")

            # Extract parameters
            param_ref_dic[sim] = {
                param: get_config_value(param_file, param) for param in parameter_list
            }

        return self._prepare_dataframe(composite_scores, param_ref_dic)

    def _compute_isotope_score(self, ds_model: xr.Dataset, df_isotope_obs: pd.DataFrame,
                                target_name: str) -> float:

        df_coords = pd.DataFrame({
            "lon": df_isotope_obs["Longitude"].apply(
                lambda x: find_nearest(ds_model.lon_t.values, x)),
            "lat": df_isotope_obs["Latitude"].apply(
                lambda x: find_nearest(ds_model.lat_t.values, x)),
            "zt": df_isotope_obs["DEPTH [m]"].apply(
                lambda x: find_nearest(ds_model.z_t.values, x))
        })

        # Extract and convert model data
        model_last = ds_model.isel(time=-1)
        var_model = self._convert_dpm_to_bq(model_last, target_name)

        # Extract at observation points
        obs_df = df_isotope_obs.copy()
        obs_df[f'{target_name}_bern3d'] = df_coords.apply(
            lambda row: var_model.isel(
                lon_t=int(row['lon']),
                lat_t=int(row['lat']),
                z_t=int(row['zt'])
            ).item(),
            axis=1
        )

        # Compute weighted MAE
        abs_err = abs(obs_df[f"{target_name}_obs"] - obs_df[f"{target_name}_bern3d"])
        weight_err = abs_err / obs_df[f"{target_name}_std"]
        mae = weight_err.sum() / (1 / obs_df[f"{target_name}_std"]).sum()

        return float(mae)

    @staticmethod
    def _convert_dpm_to_bq(data: xr.Dataset, var: str) -> xr.DataArray:
        """Convert from dpm to Bq.

            Args:
                data: Dataset containing the variable to convert.
                var: Name of the variable to convert.

            Returns:
                Converted variable in Bq.
        """
        return data[var] * 10**6 / (60 * data["rho_SI"])


# Register default targets
TargetRegistry.register("physics", PhysicsTarget,
                        aliases=["temp", "salt", "ida", "amoc",
                                 "temp_salt_ida_amoc", "temperature", "salinity"])

TargetRegistry.register("npzd", NPZDTarget,
                        aliases=["npzd", "dic", "alk", "po4", "sio", "no3", "poc",
                                 "caco3", "opal", "npp"]
)
TargetRegistry.register("isotope", IsotopeTarget, aliases=["pad", "thd", "isotopes"])
