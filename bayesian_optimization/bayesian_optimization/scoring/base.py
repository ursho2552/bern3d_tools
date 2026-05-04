"""
This module defines the base class for scoring targets in the Bayesian optimization framework. The
ScoringTarget class is an abstract base class that requires implementing classes to define a name
property and a score method. The score method is responsible for computing the score based on the
given parameters, model outputs, and validation data. The module also includes a helper method to
prepare the final DataFrame with scores and parameters for further analysis.
"""

import pandas as pd
import xarray as xr
from abc import ABC, abstractmethod

class ScoringTarget(ABC):
    """ Base class for scoring targets in Bayesian optimization."""

    def __init__(self, name: str):
        self.name = name.lower()

    @abstractmethod
    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score for the given parameters and model outputs.

            Args:
                parameter_list: List of parameter set names.
                model_xr: Dictionary of xarray Datasets for each simulation.
                sims: List of simulation names corresponding to the model_xr keys.
                validation_data_path: Path to the validation data file.
                parameter_files: List of file paths for the parameter sets.
                log_files: List of file paths for the simulation logs.
                **kwargs: Additional keyword arguments for scoring.

            Returns:
                DataFrame with parameters and scores.
        """
        pass

    def _prepare_dataframe(self, scores: dict[str, float],
                           params: dict[str, dict[str, float]]) -> pd.DataFrame:
        """Helper method to prepare the final DataFrame with scores and parameters.

            Args:
                scores: List of computed scores for each parameter set.
                params: Dictionary of parameters with parameter set names as keys.

            Returns:
                DataFrame combining parameters and their corresponding scores.
        """
        score_df = pd.DataFrame({self.name: scores})
        param_df = pd.DataFrame.from_dict(params, orient="index")
        param_df[f"mae_{self.name.lower()}"] = param_df.index.map(score_df[self.name])

        return param_df
