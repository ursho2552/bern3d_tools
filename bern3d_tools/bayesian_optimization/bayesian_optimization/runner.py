
"""
Bayesian optimization module for Bern3D parameter tuning.
"""

import logging
import pickle

from skopt import Optimizer
import bayesian_optimization as bo
import bern3d_tools.shared.utils as shared_utils


class BayesianOptimizationRunner:
    """Orchestrates Bayesian optimization iterations for Bern3D parameter tuning.

    This class encapsulates the entire optimization workflow including:
    - Optimizer initialization and persistence
    - Acquisition strategy selection
    - Simulation batch submission
    - Job dependency management
    """

    # Acquisition strategy constants
    STRATEGY_HIGH_ERROR = "cl_max"
    STRATEGY_MED_ERROR = "cl_mean"
    STRATEGY_LOW_ERROR = "cl_min"

    # Error fraction thresholds for strategy selection
    FRACTION_THRESHOLD_MED = 0.3
    FRACTION_THRESHOLD_LOW = 0.1

    # File management constants
    OPTIMIZER_FILENAME = "optimizer.pkl"
    RESULTS_FILENAME_TEMPLATE = "{target}_df_simulations.csv"

    def __init__(self, configuration_file: str, current_iteration: int, email: str):
        """Initialize the optimization runner.

        Args:
            configuration_file: Path to configuration YAML file
            current_iteration: Current iteration number (0 for initialization)
            email: Email address for job notifications
        """
        self.config = shared_utils.read_config_file(configuration_file, bo.ConfigParameters)
        self.config = bo.check_configuration(self.config)
        self.current_iteration = current_iteration
        self.email = email
        self.optimizer = None

    def run(self) -> None:
        """Execute one iteration of Bayesian optimization."""
        # Initialize or load optimizer
        if self.current_iteration == 0:
            self._initialize_optimizer()
        else:
            self._load_optimizer()

        # Ask for next parameters and submit batch
        next_parameters = self._ask_next_parameters()
        self._save_optimizer()

        # Submit simulations and chain dependent jobs
        self._submit_simulation_batch(next_parameters)

    # Initialization Methods

    def _initialize_optimizer(self) -> None:
        """Initialize optimizer for first iteration."""
        if self.config.initialization_type == "simulation":
            self._initialize_optimizer_from_simulation()
        else:
            self._initialize_optimizer_random()

    def _initialize_optimizer_from_simulation(self) -> None:
        """Initialize optimizer using existing simulation results."""
        logging.info("Initialize with a simulation")

        # Create optimizer with single initial point
        parameter_bounds = list(self.config.parameter_bounds.values())
        self.optimizer = Optimizer(
            parameter_bounds,
            base_estimator=self.config.surrogate_type,
            acq_func=self.config.acquisition_type,
            acq_optimizer=self.config.acquisitition_optimizer,
            n_jobs=self.config.job_number,
            n_initial_points=1,
            initial_point_generator="lhs"
        )

        # Load and score initial simulations
        initial_df = self._load_and_score_initial_simulations()

        # Save results
        results_file = self.RESULTS_FILENAME_TEMPLATE.format(target=self.config.tuning_target)
        initial_df.to_csv(f"{self.config.output_dir_optimizer}/{results_file}")

    def _initialize_optimizer_random(self) -> None:
        """Initialize optimizer with random points."""
        logging.info("Initialize with %s", self.config.initialization_type)

        parameter_bounds = list(self.config.parameter_bounds.values())
        self.optimizer = Optimizer(
            parameter_bounds,
            base_estimator=self.config.surrogate_type,
            acq_func=self.config.acquisition_type,
            acq_optimizer=self.config.acquisitition_optimizer,
            n_jobs=self.config.job_number,
            n_initial_points=self.config.n_initialization,
            initial_point_generator=self.config.initialization_type
        )

    def _load_and_score_initial_simulations(self) -> 'pd.DataFrame':
        """Load initial simulation data and compute scores.

        Returns:
            DataFrame with scored simulations
        """
        simulation_dict = bo.access_file(
            model_output_files=self.config.output_files_restart,
            simulation_name=self.config.simulation_name_restart,
            output_type=self.config.output_type_bern3d,
            output_timescale=self.config.output_timescale_bern3d,
            simulation_initialization=True,
            wildcard=self.config.wildcard_simulation
        )

        parameter_list = list(self.config.parameter_bounds.keys())

        # Prepare kwargs for scoring function
        function_kwargs = {
            'variable_names': self.config.variable_names,
            'use_penalty': self.config.use_penalty,
            **self.config.target_values
        }

        initial_df, self.optimizer = bo.compute_and_tell_optimizer(
            optimizer=self.optimizer,
            target=self.config.tuning_target,
            parameter_list=parameter_list,
            simulation_dict=simulation_dict,
            validation_data_path=self.config.validation_data_path,
            parameter_file_template=self.config.bern3d_parameter_file,
            **function_kwargs
        )

        return initial_df

    # Optimizer Persistence Methods

    def _load_optimizer(self) -> None:
        """Load optimizer from previous iteration."""
        logging.info("Loading the optimizer from the previous iteration")
        optimizer_path = f"{self.config.output_dir_optimizer}/{self.OPTIMIZER_FILENAME}"

        with open(optimizer_path, 'rb') as optimizer_file:
            self.optimizer = pickle.load(optimizer_file)

    def _save_optimizer(self) -> None:
        """Save optimizer state to disk."""
        optimizer_path = f"{self.config.output_dir_optimizer}/{self.OPTIMIZER_FILENAME}"

        with open(optimizer_path, 'wb') as optimizer_file:
            pickle.dump(self.optimizer, optimizer_file)

    # Acquisition Methods

    def _ask_next_parameters(self) -> list:
        """Ask optimizer for next parameters to test.

        Returns:
            List of parameter sets to evaluate
        """
        strategy, num_points = self._determine_acquisition_strategy()

        logging.info("Asking for %d parameters with strategy '%s'", num_points, strategy)
        next_parameters = self.optimizer.ask(n_points=num_points, strategy=strategy)

        # Ensure list format for batch processing
        if self.config.batchsize == 1:
            next_parameters = [next_parameters]

        return next_parameters

    def _determine_acquisition_strategy(self) -> tuple[str, int]:
        """Determine acquisition strategy based on optimization progress.

        Returns:
            Tuple of (strategy_name, number_of_points)
        """
        # First iteration: use default strategy
        if not hasattr(self.optimizer, 'first_error'):
            logging.info("Asking for initial parameters to test")
            self.optimizer.stable_iterations = 0
            self.optimizer.max_stable_iterations = self.config.max_stable_iterations
            return self.STRATEGY_HIGH_ERROR, self.config.batchsize

        # Subsequent iterations: adapt based on error fraction
        logging.info("Asking for next parameters to test in iteration %d", self.current_iteration)

        current_error = self.optimizer.get_result().fun
        fraction = max(1, current_error / self.optimizer.first_error)

        # Determine strategy based on fraction
        if fraction < self.FRACTION_THRESHOLD_LOW:
            strategy = self.STRATEGY_LOW_ERROR
        elif fraction < self.FRACTION_THRESHOLD_MED:
            strategy = self.STRATEGY_MED_ERROR
        else:
            strategy = self.STRATEGY_HIGH_ERROR

        # Scale number of points based on fraction
        num_points = max(int(self.config.batchsize * fraction), 2)

        return strategy, num_points

    # Simulation Submission Methods

    def _submit_simulation_batch(self, next_parameters: list) -> None:
        """Submit batch of simulations and chain dependent jobs.

        Args:
            next_parameters: List of parameter sets to evaluate
        """
        # Prepare parameters (add reference simulation if needed)
        parameters_to_run = self._prepare_parameter_batch(next_parameters)

        # Submit all simulations
        simulation_ids = []
        simulation_names = []

        for batch_number, param_config in enumerate(parameters_to_run):
            sim_id, sim_name = self._setup_and_submit_simulation(batch_number, param_config)
            simulation_ids.append(sim_id)
            simulation_names.append(sim_name)

        # Chain postprocessing job
        postprocessing_id = self._submit_postprocessing_job(simulation_ids, simulation_names)

        # Chain next optimization iteration (if not done)
        if not self._check_if_optimization_done():
            self._submit_next_optimizer_iteration(postprocessing_id)

    def _prepare_parameter_batch(self, next_parameters: list) -> list[dict]:
        """Prepare parameter batch, adding reference simulation if needed.

        Args:
            next_parameters: List of parameter sets

        Returns:
            List of parameter configurations with metadata
        """
        batch_offset = 0
        parameters_to_run = []

        # Add reference simulation for first iteration (if not initialized from simulation)
        if (self.current_iteration == 0 and
            self.config.initialization_type != "simulation"):
            parameters_to_run.append({'parameters': None, 'is_reference': True})
            batch_offset = 1

        # Add regular parameter sets
        for params in next_parameters:
            parameters_to_run.append({
                'parameters': params,
                'is_reference': False,
                'batch_offset': batch_offset
            })

        return parameters_to_run

    def _setup_and_submit_simulation(self, batch_number: int,
                                     param_config: dict) -> tuple[str, str]:
        """Setup and submit a single simulation.

        Args:
            batch_number: Batch number for naming
            param_config: Parameter configuration dictionary

        Returns:
            Tuple of (job_id, simulation_name)
        """
        # Get configuration for this simulation
        sim_config = self._get_simulation_setup_config(batch_number, param_config)

        # Setup run directory
        new_simulation_path = shared_utils.setup_run_directory(
            template_dir=sim_config['template_dir'],
            executable_name=sim_config['executable_name'],
            new_name=sim_config['simulation_name'],
            work_dir=self.config.work_directory,
            restart_files=sim_config['restart_files']
        )

        # Update parameter files
        self._update_parameter_files(
            new_simulation_path,
            sim_config['simulation_name'],
            param_config['parameters'],
            sim_config['fixed_values'],
            sim_config['names_fixed']
        )

        # Submit job
        job_id = shared_utils.submit_job(
            script_template=self.config.bern3d_script,
            executable_name=sim_config['simulation_name'],
            executable_path=new_simulation_path,
            time=self.config.bern3d_script_time,
            header_command=f"--mail-user={self.email}"
        )

        return job_id, sim_config['simulation_name']

    def _get_simulation_setup_config(self, batch_number: int,
                                     param_config: dict) -> dict:
        """Get configuration for simulation setup.

        Args:
            batch_number: Batch number for naming
            param_config: Parameter configuration

        Returns:
            Dictionary with simulation setup configuration
        """
        if param_config['is_reference']:
            return {
                'simulation_name': bo.optimizer.REFERENCE_SIM_NAME,
                'template_dir': self.config.bern3d_template,
                'executable_name': self.config.bern3d_executable_name,
                'restart_files': self.config.bern3d_restart_files,
                'fixed_values': [],
                'names_fixed': []
            }
        else:
            batch_offset = param_config.get('batch_offset', 0)
            sim_name = (f"{self.config.simulation_name_bern3d}_"
                       f"{str(batch_number - batch_offset).zfill(2)}_"
                       f"{str(self.current_iteration).zfill(3)}")

            return {
                'simulation_name': sim_name,
                'template_dir': f"{self.config.work_directory}/run/",
                'executable_name': bo.optimizer.REFERENCE_SIM_NAME,
                'restart_files': None,
                'fixed_values': (list(self.config.fixed_values.values())
                               if self.config.fixed_values else []),
                'names_fixed': (list(self.config.fixed_values.keys())
                              if self.config.fixed_values else [])
            }

    def _update_parameter_files(self, simulation_path: str, simulation_name: str,
                               parameters: list | None, fixed_values: list,
                               names_fixed: list) -> None:
        """Update parameter files for a simulation.

        Args:
            simulation_path: Path to simulation directory
            simulation_name: Name of simulation
            parameters: Parameter values (None for reference)
            fixed_values: Fixed parameter values
            names_fixed: Names of fixed parameters
        """
        parameter_file_templates = self.config.bern3d_parameter_file.split(",")
        parameter_names = list(self.config.parameter_bounds.keys())

        for param_file_template in parameter_file_templates:
            param_file = f"{simulation_path}/{simulation_name}{param_file_template}"

            # Parse existing file
            parameter_dict, preserved_lines = shared_utils.parse_to_dict(file_path=param_file)

            # Update tuned parameters (if not reference)
            if parameters is not None:
                parameter_dict = shared_utils.adapt_dictionary(
                    config_dict=parameter_dict,
                    parameter=parameter_names,
                    factor=1,
                    new_value=parameters
                )

            # Update fixed parameters
            for name, value in zip(names_fixed, fixed_values):
                parameter_dict = shared_utils.adapt_dictionary(
                    config_dict=parameter_dict,
                    parameter=[name],
                    factor=1,
                    new_value=[value]
                )

            # Write updated file
            shared_utils.create_new_parameter_file(
                config_dict=parameter_dict,
                parameter_file_name=param_file,
                preserved_lines=preserved_lines
            )

    # Job Chaining Methods

    def _submit_postprocessing_job(self, simulation_ids: list[str],
                                   simulation_names: list[str]) -> str:
        """Submit postprocessing job dependent on simulations.

        Args:
            simulation_ids: List of simulation job IDs
            simulation_names: List of simulation names

        Returns:
            Postprocessing job ID
        """
        simulation_names_str = ",".join(simulation_names)
        command_line_args = [self.config.config_file_path, simulation_names_str]

        executable_name = f"{self.config.python_scripts}/postprocessing.py"

        postprocessing_id = shared_utils.submit_job(
            script_template=self.config.postprocessing_script,
            executable_name=executable_name,
            executable_path=self.config.work_directory,
            time=self.config.postprocessing_script_time,
            header_command=f"--mail-user={self.email}",
            dependency=simulation_ids,
            dependency_type="afterany",
            command_line_arg=command_line_args
        )

        return postprocessing_id

    def _submit_next_optimizer_iteration(self, postprocessing_id: str) -> str:
        """Submit next optimizer iteration dependent on postprocessing.

        Args:
            postprocessing_id: Postprocessing job ID

        Returns:
            Next optimizer job ID
        """
        next_iteration = self.current_iteration + 1
        logging.info("Calling the optimizer for the next iteration: %d", next_iteration)

        command_line_args = [
            self.config.config_file_path,
            str(next_iteration),
            self.email
        ]

        executable_name = f"{self.config.python_scripts}/main.py"

        optimizer_id = shared_utils.submit_job(
            script_template=self.config.optimizer_script,
            executable_name=executable_name,
            executable_path=self.config.work_directory,
            time=self.config.optimizer_script_time,
            header_command=f"--mail-user={self.email}",
            dependency=[postprocessing_id],
            command_line_arg=command_line_args
        )

        return optimizer_id

    def _check_if_optimization_done(self) -> bool:
        """Check if optimization is complete.

        Returns:
            True if optimization should stop
        """
        return bo.check_optimization_status(
            self.optimizer,
            self.current_iteration + 1,
            self.config.max_iterations
        )
