# This file initializes the `bayesian_optimization` module.
"""Bayesian optimization module for Bern3D parameter tuning."""

# Import specific items from each module
from bayesian_optimization.runner import BayesianOptimizationRunner
from bayesian_optimization.optimizer import (
    compute_and_tell_optimizer,
    check_optimization_status,
    REFERENCE_SIM_NAME,
)
from bayesian_optimization.utils import (
    access_file,
    check_configuration,
    ConfigParameters,
    # Add other public functions/classes from utils here
)

# Define what gets exported with "import bayesian_optimization as bo"
__all__ = [
    # Runner
    'BayesianOptimizationRunner',
    # Optimizer
    'compute_and_tell_optimizer',
    'check_optimization_status',
    'REFERENCE_SIM_NAME',
    # Utils
    'access_file',
    'check_configuration',
    'ConfigParameters',
]
