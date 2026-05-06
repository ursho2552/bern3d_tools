# This file initializes the `bayesian_optimization` module.
"""Bayesian optimization module for Bern3D parameter tuning."""

# Import specific items from each module
from .runner import BayesianOptimizationRunner
from .postprocessing_runner import PostprocessingRunner
from .optimizer import (
    compute_and_tell_optimizer,
    check_optimization_status,
    REFERENCE_SIM_NAME,
)
from . import custom_targets
from .utils import (
    access_file,
    check_configuration,
    ConfigParameters,
    # Add other public functions/classes from utils here
)
from .scoring.utils import (
    simulation_finished,
    nrmse,
    get_field_stability,
    get_config_value
)
from .scoring.base import ScoringTarget
from .scoring.protocols import ScoringTargetProtocol
from .scoring.targets import TargetRegistry

# Define what gets exported with "import bayesian_optimization as bo"
__all__ = [
    # Runner
    'BayesianOptimizationRunner',
    'PostprocessingRunner',
    # Optimizer
    'compute_and_tell_optimizer',
    'check_optimization_status',
    'REFERENCE_SIM_NAME',
    # Utils
    'access_file',
    'check_configuration',
    'simulation_finished',
    'nrmse',
    'get_field_stability',
    'get_config_value',
    'ConfigParameters',
    'TargetRegistry',
    'ScoringTarget',
    'ScoringTargetProtocol',
    # Custom targets (auto-registered, but also available for direct import)
    'custom_targets',
]
