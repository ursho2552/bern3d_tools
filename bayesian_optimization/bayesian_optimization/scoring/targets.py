"""
Module for defining scoring targets for Bayesian optimization in the BGC model context.
This includes both default targets (e.g., temperature and salinity) and a registry for
custom targets.
"""
import pandas as pd
import xarray as xr
import numpy as np

from .protocols import ScoringTargetProtocol
from .base import ScoringTarget

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

        This method should be implemented to compute the score based on the specific physical metric.
        """
        # Placeholder implementation
        scores = [0.0] * len(parameter_list)  # Dummy scores for demonstration
        params = {param: {} for param in parameter_list}  # Dummy parameters for demonstration

        return self._prepare_dataframe(scores, params)

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
