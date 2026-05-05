#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the evaluation script for the sensitivtiy analysis module.
"""
import xarray as xr
import numpy as np
import pandas as pd
import logging
from pathlib import Path
from typing import TypeVar

ConfigFile = TypeVar('ConfigFile')

def analyze_sensitivity_results(config: ConfigFile,
                                parameter_list: list[str]) -> pd.DataFrame:
    """
    Analyze sensitivity results by comparing model outputs to reference run.

    Parameters:
    config (ConfigParameters): Configuration parameters
    parameter_list (List[str]): List of parameters that were varied

    Returns:
    pd.DataFrame: Summary of sensitivity analysis results
    """

    results = []
    results_dir = Path(config.work_directory) / "results"

    # Load reference data for each target field
    reference_data = {}
    for variable, filename_suffix in config.target_field.items():
        ref_file = results_dir / f"Reference{filename_suffix}"
        if ref_file.exists():
            with xr.open_dataset(ref_file, decode_times=False) as ds:
                if variable in ds:
                    # Get last timestep
                    ref_data = ds[variable].isel(time=-1)
                    reference_data[variable] = ref_data
                    logging.info(f"Loaded reference data for {variable}: shape {ref_data.shape}")
                else:
                    # End execution if reference variable is missing
                    raise ValueError(f"Reference variable {variable} missing in {ref_file}")
        else:
            # End execution if reference file is missing
            raise FileNotFoundError(f"Reference file {ref_file} not found")

    # Analyze each parameter variation
    parameter_factor_dict = config.parameter_list

    for parameter in parameter_list:
        if parameter is None:  # Skip the None entry used for reference
            continue

        if isinstance(parameter_factor_dict[parameter], list):
            change_factors = parameter_factor_dict[parameter]
            names = [f"{str(factor).replace('.','p')}" for factor in change_factors]

        else:
            names = ["Low", "High"]

        for variation in names:
            run_name = f"{variation}_{parameter}"

            # Analyze each target field
            for variable, filename_suffix in config.target_field.items():
                if variable not in reference_data:
                    continue

                file_path = results_dir / f"{run_name}{filename_suffix}"

                if not file_path.exists():
                    logging.error(f"Model run failed - file not found: {file_path}")
                    # Add a failure record to track missing runs
                    results.append({
                        'parameter': parameter,
                        'variation': variation,
                        'variable': variable,
                        'dimensions': None,
                        'reference_mean': np.nan,
                        'sensitivity_mean': np.nan,
                        'absolute_difference': np.nan,
                        'relative_difference_percent': np.nan,
                        'max_absolute_difference': np.nan,
                        'mean_absolute_difference': np.nan,
                        'std_difference': np.nan
                    })
                    continue

                try:
                    # Load the dataset
                    with xr.open_dataset(file_path, decode_times=False) as ds:
                        if variable not in ds:
                            logging.warning(f"Variable {variable} not found in {file_path}")
                            continue

                        # Get last timestep
                        var_data = ds[variable].isel(time=-1)
                        ref_data = reference_data[variable]

                        # Calculate sensitivity metrics
                        sensitivity_metrics = calculate_sensitivity_metrics(
                            var_data, ref_data, parameter, variation, variable
                        )

                        results.append(sensitivity_metrics)

                except Exception as e:
                    logging.error(f"Error processing {file_path}: {e}")
                    continue

    return pd.DataFrame(results)

def calculate_sensitivity_metrics(var_data: xr.DataArray, ref_data: xr.DataArray,
                                parameter: str, variation: str, variable: str) -> dict:
    """
    Calculate sensitivity metrics between variable data and reference.

    Parameters:
    var_data (xr.DataArray): Variable data from sensitivity run
    ref_data (xr.DataArray): Reference data
    parameter (str): Parameter name
    variation (str): "Low" or "High"
    variable (str): Variable name

    Returns:
    Dict: Dictionary with sensitivity metrics
    """

    # Calculate global means
    var_mean = var_data.mean(skipna=True).values
    ref_mean = ref_data.mean(skipna=True).values

    # Calculate absolute and relative differences
    abs_diff = var_mean - ref_mean
    rel_diff = (abs_diff / ref_mean) * 100 if ref_mean != 0 else np.nan

    # Calculate spatial statistics
    spatial_diff = var_data - ref_data
    spatial_abs_diff = np.abs(spatial_diff)

    max_abs_diff = spatial_abs_diff.max().values
    mean_abs_diff = spatial_abs_diff.mean().values

    # Calculate standard deviation of differences
    std_diff = spatial_diff.std().values

    # Determine data dimensions
    dims = len(var_data.dims)
    dimension_info = f"{dims}D: {list(var_data.dims)}"

    # check if variable has a p surrounded by numbers, if so replace with . for better readability
    if "p" in variation and any(char.isdigit() for char in variation):
        variation = variation.replace("p", ".")

    return {
        'parameter': parameter,
        'variation': variation,
        'variable': variable,
        'dimensions': dimension_info,
        'reference_mean': ref_mean,
        'sensitivity_mean': var_mean,
        'absolute_difference': abs_diff,
        'relative_difference_percent': rel_diff,
        'max_absolute_difference': max_abs_diff,
        'mean_absolute_difference': mean_abs_diff,
        'std_difference': std_diff
    }

def save_sensitivity_summary(df: pd.DataFrame, output_dir: str) -> None:
    """
    Save sensitivity analysis summary to files.

    Parameters:
    df (pd.DataFrame): Sensitivity results dataframe
    output_dir (str): Output directory path
    """

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Save full results
    csv_file = output_path / "sensitivity_analysis_results.csv"
    df.to_csv(csv_file, index=False)
    logging.info(f"Saved detailed results to {csv_file}")

    # Create summary by parameter
    summary = df.groupby(['parameter', 'variable']).agg({
        'relative_difference_percent': ['mean', 'std'],
        'mean_absolute_difference': ['mean', 'std']
    }).round(4)

    summary_file = output_path / "sensitivity_summary.csv"
    summary.to_csv(summary_file)
    logging.info(f"Saved summary to {summary_file}")

    # Print top sensitivities
    logging.info("\nTop 10 Most Sensitive Parameters (by absolute relative difference):")
    top_sensitive = df.loc[df['relative_difference_percent'].abs().nlargest(10).index]
    logging.info(top_sensitive[['parameter', 'variation', 'variable', 'relative_difference_percent']].to_string(index=False))
