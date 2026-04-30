"""

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
