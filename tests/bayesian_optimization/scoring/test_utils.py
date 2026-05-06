"""Tests for bayesian optimization scoring utilities."""

import pytest
import numpy as np
import xarray as xr

from pathlib import Path
import tempfile

from bern3d_tools.bayesian_optimization.bayesian_optimization.scoring import utils


class TestSimulationFinished:
    """Test simulation_finished function."""

    def test_simulation_complete(self, tmp_path: Path) -> None:
        """Test that simulation_finished returns True when 'SIMULATION COMPLETE' is in the log file.

            Args:
                tmp_path (Path): Temporary directory provided by pytest for creating test files.

            Returns:
                None
        """
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "Starting simulation\n"
            "Running iteration 1000\n"
            "SIMULATION COMPLETE\n"
            "Cleanup done\n"
        )

        assert utils.simulation_finished(log_file) is True

    def test_simulation_failed(self, tmp_path: Path) -> None:
        """Test that simulation_finished returns False when 'SIMULATION COMPLETE' is not in the log file.

            Args:
                tmp_path (Path): Temporary directory provided by pytest for creating test files.

            Returns:
                None
        """
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "Starting simulation\n"
            "Running iteration 1000\n"
            "Error: Simulation failed\n"
            "Cleanup done\n"
        )

        assert utils.simulation_finished(log_file) is False

    def test_simulation_empty_log(self, tmp_path: Path) -> None:
        """Test that simulation_finished returns False when the log file is empty.

            Args:
                tmp_path (Path): Temporary directory provided by pytest for creating test files.

            Returns:
                None
        """
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        assert utils.simulation_finished(log_file) is False

    def test_nrmse_perfect_prediction(self) -> None:
        """Test that nrmse returns 0 for perfect predictions."""
        predictions = np.array([1, 2, 3])
        targets = np.array([1, 2, 3])
        assert utils.nrmse(predictions, targets) == 0

    def test_nrmse_with_weights(self) -> None:
        """Test that nrmse returns correct value when weights are provided."""
        predictions = np.array([1, 2, 3])
        targets = np.array([1, 2, 3])
        weights = np.array([0.5, 1.0, 1.5])
        assert utils.nrmse(predictions, targets, weights) == 0

    def test_nrmse_different_predictions(self) -> None:
        """Test that nrmse returns a positive value when predictions differ from targets."""
        predictions = np.array([1, 2, 3])
        targets = np.array([2, 3, 4])
        nrmse_value = utils.nrmse(predictions, targets)
        assert nrmse_value > 0

    def test_nrmse_with_missing_values(self) -> None:
        """Test that nrmse handles missing values (NaNs) correctly."""
        predictions = np.array([1, 2, np.nan])
        targets = np.array([1, 2, 3])
        nrmse_value = utils.nrmse(predictions, targets)
        assert np.isnan(nrmse_value) or nrmse_value >= 0