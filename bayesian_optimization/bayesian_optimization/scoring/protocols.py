"""
This module defines the ScoringTargetProtocol, which specifies the interface for scoring target in
the Bayesian optimization framework.

This protocol requires implementing classes with a name property and a score method. The score
method takes in a list of parameters, model output dictionary, simulation names, a validation data
path, parameter files, log files, and any additional keyword arguments. The method should return a
DataFrame containing a specific structure (TBD)
"""

from typing import Protocol
import pandas as pd
import xarray as xr

class ScoringTargetProtocol(Protocol):
    """ Protocol defining the interface for scoring targets.

    Any class implementing this protocol can be used as a custom scoring target.
    """

    @property
    def name(self) -> str:
        """ Target name (e.g., temp_salt_amoc). """
        ...

    def score(self, parameter_list: list[str], model_xr: dict[str, xr.Dataset],
              sims: list[str], validation_data_path: str,
              parameter_files: list[str], log_files: list[str],
              **kwargs) -> pd.DataFrame:
        """ Compute the score for the given parameters and model outputs.

        Returns:
            DataFrame with parameters and scores.
        """
        ...
