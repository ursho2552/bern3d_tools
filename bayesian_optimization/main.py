#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for Bayesian optimization of Bern3D parameters.
"""

import os
import sys
# add the grand-parent dir (repo root) to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

import argparse
import logging

import numpy as np
import bern3d_tools.shared.utils as shared_utils
import bayesian_optimization as bo


def main(configuration_file: str, current_iteration: int, email: str) -> None:
    """Execute one iteration of Bayesian optimization.

    Args:
        configuration_file: Path to configuration YAML file
        current_iteration: Current iteration number (0 for first)
        email: Email address for job notifications
    """
    runner = bo.BayesianOptimizationRunner(configuration_file, current_iteration, email)
    runner.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Run Bayesian optimization of Bern3D parameters')
    parser.add_argument('--config_file', required=True, type=str,
                       help='Path to the configuration file')
    parser.add_argument('--current_iteration', required=False, type=int, default=0,
                       help='Current iteration number (default: 0)')
    parser.add_argument("--email", required=False, type=str,
                       help='Email address for job notifications')

    args = parser.parse_args()

    if args.email is None:
        args.email = shared_utils.get_user_email()

    np.random.seed(args.current_iteration)

    main(args.config_file, args.current_iteration, args.email)
