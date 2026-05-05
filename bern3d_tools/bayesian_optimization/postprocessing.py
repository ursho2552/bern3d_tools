#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Postprocessing for Bayesian optimization.
"""

import argparse
import logging

import bayesian_optimization as bo

def main(configuration_file: str, simulation_names: str) -> None:
    """Execute postprocessing after simulations complete.

    Args:
        configuration_file: Path to configuration YAML file
        simulation_names: Comma-separated list of simulation names
    """
    runner = bo.PostprocessingRunner(configuration_file, simulation_names)
    runner.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description='Postprocessing for Bayesian optimization'
    )
    parser.add_argument('--config_file', required=True, type=str,
                       help='Path to the configuration file')
    parser.add_argument('--simulation_name', required=True, type=str,
                       help='Comma-separated simulation names')

    args = parser.parse_args()

    main(args.config_file, args.simulation_name)
