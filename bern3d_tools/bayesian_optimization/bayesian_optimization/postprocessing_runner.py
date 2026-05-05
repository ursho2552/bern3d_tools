"""Postprocessing runner for Bayesian optimization."""

import os

import pickle
import logging

import pandas as pd
import bayesian_optimization as bo
import bern3d_tools.shared.utils as shared_utils

class PostprocessingRunner:
    """Orchestrates postprocessing after Bern3D simulations complete.

    This class encapsulates:
    - Loading optimizer state
    - Computing scores from simulation outputs
    - Updating optimizer with results
    - Tracking optimization convergence
    """

    OPTIMIZER_FILENAME = "optimizer.pkl"
    RESULTS_FILENAME_TEMPLATE = "{target}_df.csv"

    def __init__(self, configuration_file: str, simulation_names: str):
        """Initialize the postprocessing runner.

        Args:
            configuration_file: Path to configuration YAML file
            simulation_names: Comma-separated list of simulation names
        """
        self.config = shared_utils.read_config_file(configuration_file, bo.ConfigParameters)
        self.config = bo.check_configuration(self.config)
        self.simulation_names = simulation_names.split(",")
        self.optimizer = None
        self.first_iteration = False

    def run(self) -> None:
        """Execute postprocessing workflow."""
        # Load optimizer
        self._load_optimizer()

        # Check if this is first iteration
        self._check_first_iteration()

        # Load simulation results and compute scores
        new_df = self._compute_scores()

        # Update results dataframe
        self._update_results_dataframe(new_df)

        # Update convergence tracking
        self._update_convergence_tracking()

        # Save optimizer
        self._save_optimizer()

    # Private Methods

    def _load_optimizer(self) -> None:
        """Load optimizer from previous state."""
        optimizer_path = f"{self.config.output_dir_optimizer}/{self.OPTIMIZER_FILENAME}"

        with open(optimizer_path, 'rb') as optimizer_file:
            self.optimizer = pickle.load(optimizer_file)

    def _save_optimizer(self) -> None:
        """Save optimizer state."""
        optimizer_path = f"{self.config.output_dir_optimizer}/{self.OPTIMIZER_FILENAME}"

        with open(optimizer_path, 'wb') as optimizer_file:
            pickle.dump(self.optimizer, optimizer_file)

    def _check_first_iteration(self) -> None:
        """Check if this is the first iteration."""
        results_file = self.RESULTS_FILENAME_TEMPLATE.format(target=self.config.tuning_target)
        results_path = f"{self.config.output_dir_optimizer}/{results_file}"

        self.first_iteration = not os.path.exists(results_path)

    def _compute_scores(self) -> pd.DataFrame:
        """Compute scores for completed simulations.

        Returns:
            DataFrame with simulation results and scores
        """
        # Load simulation outputs
        simulation_dict = bo.access_file(
            model_output_files=self.config.output_files_bern3d,
            simulation_name=self.simulation_names,
            output_type=self.config.output_type_bern3d,
            output_timescale=self.config.output_timescale_bern3d
        )

        # Prepare scoring arguments
        parameter_list = list(self.config.parameter_bounds.keys())
        function_kwargs = {
            'variable_names': self.config.variable_names,
            'use_penalty': self.config.use_penalty,
            **self.config.target_values
        }

        # Compute scores and update optimizer
        new_df, self.optimizer = bo.compute_and_tell_optimizer(
            optimizer=self.optimizer,
            target=self.config.tuning_target,
            parameter_list=parameter_list,
            simulation_dict=simulation_dict,
            validation_data_path=self.config.validation_data_path,
            parameter_file_template=self.config.bern3d_parameter_file,
            **function_kwargs
        )

        return new_df

    def _update_results_dataframe(self, new_df: pd.DataFrame) -> None:
        """Update results CSV with new simulation data.

        Args:
            new_df: DataFrame with new simulation results
        """
        results_file = self.RESULTS_FILENAME_TEMPLATE.format(target=self.config.tuning_target)
        results_path = f"{self.config.output_dir_optimizer}/{results_file}"

        if self.first_iteration:
            # First iteration: initialize tracking
            self._initialize_error_tracking(new_df)
            updated_df = new_df
        else:
            # Subsequent iterations: append to existing results
            current_df = pd.read_csv(results_path, index_col=0)
            updated_df = pd.concat([current_df, new_df])

        updated_df.to_csv(results_path)
        logging.info(f"Updated results saved to {results_path}")

    def _initialize_error_tracking(self, df: pd.DataFrame) -> None:
        """Initialize error tracking for first iteration.

        Args:
            df: DataFrame with first batch of results
        """
        # Check if reference simulation was used
        has_reference = "Reference" in df.index[0]
        use_reference = self.config.use_reference_simulation

        if has_reference and use_reference:
            # Use reference simulation error
            first_error = df.iloc[0][-1]
        else:
            # Use mean of initial function values
            first_error = self.optimizer.get_result().func_vals.mean()

        self.optimizer.first_error = first_error
        self.optimizer.last_error = first_error
        self.optimizer.stable_iterations = 0

        logging.info(f"Initialized first_error to {first_error:.4f}")

    def _update_convergence_tracking(self) -> None:
        """Update convergence tracking based on current error."""
        current_error = self.optimizer.get_result().fun

        if current_error < self.optimizer.last_error:
            # Improved - reset stability counter
            self.optimizer.last_error = current_error
            self.optimizer.stable_iterations = 0
            logging.info(f"Error improved to {current_error:.4f}")
        else:
            # No improvement - increment stability counter
            self.optimizer.stable_iterations += 1
            logging.info(
                f"Error plateaued at {current_error:.4f} "
                f"(stable for {self.optimizer.stable_iterations} iterations)"
            )
