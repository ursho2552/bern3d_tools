#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the optimizer script for the Bayesian optimization module.
"""

import logging

from pathlib import Path
import pandas as pd
import xarray as xr
import numpy as np
from skopt import Optimizer

from .scoring.targets import TargetRegistry
from .scoring.base import SCORE_COLUMN

# Constants
FAILED_SIMULATION_SCORE = 1e6
REFERENCE_SIM_NAME = "Reference"
DEFAULT_PENALTY_MULTIPLIER = 2.0

def _build_file_paths(simulation_names: list[str],
                      param_template: str) -> tuple[list[list[str]], list[str]]:
    """Build parameter file and log file paths for simulations.

    Args:
        simulation_names: List of simulation file paths
        param_template: Template for parameter files (comma-separated)

    Returns:
        Tuple of (parameter_files, log_files)
    """
    parameter_files = []
    log_files = []
    template_parts = param_template.split(",")

    for sim_path in simulation_names:
        root_dir = Path(sim_path).parent.parent
        sim_name = Path(sim_path).name.split(".")[0]

        # Determine run directory
        run_specific = root_dir / f"run_{sim_name}"
        run_dir = run_specific if run_specific.exists() else root_dir / "run"

        # Build parameter file paths
        param_paths = [str(run_dir / f"{sim_name}{part}") for part in template_parts]
        parameter_files.append(param_paths)

        # Build log file path
        log_files.append(str(run_dir / f"{sim_name}.out"))

    return parameter_files, log_files

def _extract_reference_row(df: pd.DataFrame) -> tuple[pd.Series | None, pd.DataFrame]:
    """Extract reference simulation row from dataframe.

    Args:
        df: DataFrame with simulation results

    Returns:
        Tuple of (reference_row, dataframe_without_reference)
    """
    for index_str in df.index:
        if REFERENCE_SIM_NAME in index_str:
            reference_row = df.loc[index_str].copy()
            reference_row.name = REFERENCE_SIM_NAME
            df_clean = df.drop(index=index_str)
            return reference_row, df_clean

    return None, df.copy()

def _compute_penalty(optimizer: Optimizer, target_values: np.ndarray,
                    multiplier: float) -> float:
    """Compute penalty value for failed simulations.

    Args:
        optimizer: Optimizer instance
        target_values: Array of target values (may contain NaN)
        multiplier: Penalty multiplier

    Returns:
        Penalty value
    """
    # Try to use optimizer history for penalty
    try:
        error_values = optimizer.get_result().func_vals
        n_initial = optimizer.get_result().specs['args']['n_initial_points']
        if len(error_values) >= n_initial:
            return multiplier * np.mean(error_values)
    except:
        pass

    # Fallback to mean of current values
    return multiplier * np.nanmean(target_values)

def _handle_failed_simulations_with_penalty(df: pd.DataFrame, optimizer: Optimizer,
                                           multiplier: float = DEFAULT_PENALTY_MULTIPLIER
                                           ) -> tuple[list[float], list[list[float]]]:
    """Handle failed simulations by assigning penalty scores.

    Args:
        df: DataFrame with scores
        optimizer: Optimizer instance
        multiplier: Penalty multiplier

    Returns:
        Tuple of (corrected_scores, parameters)
    """

    target_values = df[SCORE_COLUMN].values.copy()
    target_values[target_values == FAILED_SIMULATION_SCORE] = np.nan

    penalty = _compute_penalty(optimizer, target_values, multiplier)
    logging.info("Using penalty of %.4f for failed simulations", penalty)

    corrected_scores = np.where(np.isnan(target_values), penalty, target_values)

    # Extract parameters for all simulations
    param_columns = [col for col in df.columns if col != SCORE_COLUMN]
    parameters = df[param_columns].values.tolist()

    return corrected_scores.tolist(), parameters

def _handle_failed_simulations_by_removal(df: pd.DataFrame) -> tuple[list[float],
                                                                     list[list[float]],
                                                                     pd.DataFrame]:
    """Handle failed simulations by removing them.

    Args:
        df: DataFrame with scores
        target: Target name

    Returns:
        Tuple of (scores, parameters, filtered_dataframe)
    """
    target_values = df[SCORE_COLUMN].values
    failed_mask = target_values == FAILED_SIMULATION_SCORE

    n_failed = np.sum(failed_mask)
    if n_failed > 0:
        logging.info("Removed %d failed simulation(s)", n_failed)

    # Keep only successful simulations
    successful_mask = failed_mask == False
    if not np.any(successful_mask):
        raise ValueError("All simulations failed - cannot update optimizer")

    df_success = df[successful_mask].copy()
    scores = df_success[SCORE_COLUMN].values.tolist()

    param_columns = [col for col in df_success.columns if col != SCORE_COLUMN]
    parameters = df_success[param_columns].values.tolist()

    logging.info("Using %d successful simulation(s)", len(scores))
    return scores, parameters, df_success

def _simplify_indices(df: pd.DataFrame) -> pd.DataFrame:
    """Simplify dataframe indices to just simulation names.

    Args:
        df: DataFrame with path-based indices

    Returns:
        DataFrame with simplified indices
    """
    df_copy = df.copy()
    simple_indices = [idx.split("/")[-1].split(".")[0] for idx in df.index]
    df_copy.index = simple_indices
    return df_copy

def compute_and_tell_optimizer(optimizer: Optimizer, target: str,
                               parameter_list: list[str] | str,
                               simulation_dict: dict[str, xr.Dataset],
                               validation_data_path: str,
                               parameter_file_template: str,
                               **kwargs) -> tuple[pd.DataFrame, Optimizer]:
    """Compute scores and update the optimizer.

    Args:
        optimizer: Optimizer instance
        target: Target type (e.g., "temp_salt", "Pad")
        parameter_list: List of parameter names (or single string)
        simulation_dict: Dictionary mapping simulation paths to xarray Datasets
        validation_data_path: Path to validation data
        parameter_file_template: Template for parameter files (comma-separated)
        **kwargs: Additional arguments (use_penalty, variable_names, etc.)

    Returns:
        Tuple of (results_dataframe, updated_optimizer)
    """
    # Normalize parameter_list to list
    if isinstance(parameter_list, str):
        parameter_list = [parameter_list]

    use_penalty = kwargs.get('use_penalty', False)
    simulation_names = list(simulation_dict.keys())

    # Build file paths
    parameter_files, log_files = _build_file_paths(simulation_names, parameter_file_template)

    # Compute scores
    scoring_target = TargetRegistry.create(target, name=target)
    results_df = scoring_target.score(
        parameter_list=parameter_list,
        model_xr=simulation_dict,
        sims=simulation_names,
        validation_data_path=validation_data_path,
        parameter_files=parameter_files,
        log_files=log_files,
        **kwargs
    )

    # Extract reference row (if exists)
    reference_row, results_df_clean = _extract_reference_row(results_df)

    # Handle failed simulations
    if use_penalty:
        scores, parameters = _handle_failed_simulations_with_penalty(results_df_clean, optimizer)
        final_df = results_df_clean.copy()
    else:
        scores, parameters, final_df = _handle_failed_simulations_by_removal(results_df_clean)

    # Update optimizer
    optimizer.tell(parameters, scores)
    logging.info("Updated optimizer with new parameters")

    # Prepare final dataframe
    final_df = _simplify_indices(final_df)
    final_df[SCORE_COLUMN] = scores

    # Re-add reference row if it existed
    if reference_row is not None:
        final_df = pd.concat([pd.DataFrame([reference_row]), final_df])

    return final_df, optimizer

def check_optimization_status(optimizer: Optimizer, iteration: int,
                              max_iteration: int = 10) -> bool:
    """Check if optimization should stop.

    Args:
        optimizer: Optimizer instance
        iteration: Current iteration number
        max_iteration: Maximum allowed iterations

    Returns:
        True if optimization is done, False otherwise
    """
    if iteration > max_iteration:
        logging.info("Maximum iterations reached")
        return True

    if optimizer.stable_iterations >= optimizer.max_stable_iterations:
        logging.info("Maximum stable iterations reached")
        return True

    return False
