#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the script for creating Latin Hypercube Samples for the sensitivity analysis module.
"""

import numpy as np

def create_lhs_samples(parameter_list: list[str],
                       parameter_factor_dict: dict[str, list[float]],
                       num_samples: int) -> list[dict[str, float | None]]:
    """
    Create Latin Hypercube Samples for the given parameters and factors.

    Parameters:
    parameter_list (list[str]): List of parameters to sample.
    parameter_factor_dict (dict[str, list[float]]):
        Dictionary with parameters as keys and either a single change factor
        or a list of change factors as values.
    num_samples (int): Number of samples to generate.

    Returns:
    list[dict[str, float | None]]: List of dictionaries, each containing
        a sample with parameter values.
    """

    # Create the LHS matrix
    num_params = len(parameter_list)
    lhs_matrix = np.zeros((num_samples, num_params))

    for param_idx in range(num_params):
        # For each parameter, create N intervals
        # Divide [0, 1] into num_samples equal intervals
        intervals = np.arange(num_samples)

        # Shuffle the interval indices
        np.random.shuffle(intervals)

        # Sample randomly within each interval
        for sample_idx in range(num_samples):
            interval = intervals[sample_idx]
            # Sample uniformly within this interval
            # Interval bounds: [interval/num_samples, (interval+1)/num_samples]
            lower_bound = interval / num_samples
            upper_bound = (interval + 1) / num_samples
            random_value = np.random.uniform(lower_bound, upper_bound)
            lhs_matrix[sample_idx, param_idx] = random_value

    # Scale from [0, 1] to actual parameter ranges
    samples = []
    for sample_idx in range(num_samples):
        sample = {}
        for param_idx, parameter in enumerate(parameter_list):
            change_factors = parameter_factor_dict[parameter]
            low = min(change_factors)
            high = max(change_factors)

            # Scale the [0, 1] value to [low, high]
            unit_value = lhs_matrix[sample_idx, param_idx]
            scaled_value = low + unit_value * (high - low)

            sample[parameter] = scaled_value

        samples.append(sample)

    return samples
