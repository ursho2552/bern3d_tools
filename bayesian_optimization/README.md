# Bayesian Optimization Module

This module provides a framework for performing **Bayesian optimization** of model parameters, specifically designed for use with the Bern3D climate model. It automates the process of running model simulations, evaluating results, and iteratively improving parameter choices to better match observational targets.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Directory Structure](#directory-structure)
- [Extending and Customization](#extending-and-customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

This module automates the process of tuning model parameters using Bayesian optimization. It is especially useful for models like Bern3D, where the parameter space is high-dimensional.

**Key features:**
- Automated job submission and management (supports SLURM job scripts)
- Flexible configuration via YAML files
- Support for different initialization strategies (random, LHS, Sobol, etc.)
- Modular design for easy extension to other models or targets

---

## How It Works

1. **Configuration:**
   You provide a YAML configuration file specifying paths, parameter bounds, optimization settings, and targets.

2. **Initialization:**
   The optimizer generates an initial set of parameter combinations (using random, LHS, or other strategies).

3. **Simulation:**
   For each parameter set, the module:
   - Sets up a new run directory
   - Updates the model parameter files
   - Submits a simulation job to the cluster

4. **Postprocessing:**
   After simulations finish, the module:
   - Collects model outputs
   - Compares results to observational targets
   - Computes a score (e.g., mean absolute error)

5. **Optimization Loop:**
   The optimizer updates its internal model and proposes new parameter sets to test. Steps 3–5 repeat until stopping criteria are met (e.g., max iterations or convergence).

6. **Results:**
   All tested parameter sets and their scores are saved for analysis.

---

## Installation

To use this module, clone the repository and install the required dependencies

```bash
git clone <repository-url>
cd bern3d_tools/bayesian_optimization
```
---

## Configuration

All settings are controlled via a YAML configuration file. See `bayesian_optimization/config_new.yaml` for an example.

**Key fields:**
- `config_file_path`: Path to this config file
- `bern3d_script`, `postprocessing_script`, `optimizer_script`: Paths to SLURM or shell scripts for running the model, postprocessing, and optimizer
- `work_directory`: Directory for all outputs and temporary files
- `parameter_bounds`: Dictionary of parameter names and their allowed ranges
- `target_values`: Target values for model outputs (e.g., AMOC strength, POC export)
- `initialization_type`: How to generate initial parameter sets (`random`, `lhs`, etc.)
- `max_iterations`: Maximum number of optimization steps

**Example:**
```yaml
config_file_path: "/path/to/config_file.yaml"

# The path to the scripts used to run the model, postprocessing and optimizer
bern3d_script: "/path/to/run_model.sh"
postprocessing_script: "/path/to/run_postprocessing.sh"
optimizer_script: "/path/to/run_optimizer.sh"
python_scripts: "/path/to/python_scripts/"

bern3d_script_time: "04:00:00"
postprocessing_script_time: "00:30:00"
optimizer_script_time: "00:30:00"

# Name of the simulation and type of data to use
simulation_name_bern3d: "my_simulation_name"
output_type_bern3d: "full"
output_timescale_bern3d: "ave"
wildcard_simulation: !!python/none

# The path to the working directory
work_directory: "/path/to/workdirectory/"
output_files_bern3d: !!python/none
output_dir_optimizer: !!python/none

# Path to initialization in case of simulation initialization. In case of None, use !!python/none
simulation_name_restart: !!python/none
output_files_restart: !!python/none

# For Bern3d-v3, the flag has to be set to False
bern3d_f90: True
bern3d_executable_name: "RUNNAME"
bern3d_template: "/path/to/bern3D_model/run/"

# Path to validation data
validation_data_path: "/storage/scratch/users/uh24x373/bern3d_f90/run/"

# The number of iterations to run the Bayesian optimization algorithm
max_iterations: 100
max_stable_iterations: 15

# Targets for POC, CaCO3 and NPP in Pg C yr-1
# Targets for Opal in Tg Si yr-1
# In case of None, use !!python/none
target_values:
 target_amoc: 15.5
 target_poc: 9.76
 target_caco3: 1.87
 target_opal: 190.73
 target_npp: 60.0

# Path to file with parameters to be optimized
# The path should contain a keyword {my_simulation} which will be replaced by the simulation name
bern3d_parameter_file: ".npzd.parameter"
bern3d_restart_files: "/path/to/restart_file/Spinup2*"

parameter_bounds:
  a_growth_diaz: !!python/tuple [0.3,1.7]
  a_growth_other: !!python/tuple [0.3,1.7]

# Type of initialization
initialization_type: "random"
# Target of interest
tuning_target: "dic_alk_po4_sio_npp_poc_caco3_opal"
n_initialization: 5
surrogate_type: "RF"
acquisition_type: "gp_hedge"
batchsize: 10
acquisitition_optimizer: "auto"
job_number: -1
```

---

## Usage

1. **Prepare your configuration file**
   Edit a copy of `config_new.yaml` to match your system, model, and optimization goals.

2. **Ensure your template directory is ready**
   The `bern3d_template` directory should contain all files needed to run a Bern3D simulation.

3. **Run the optimizer:**
   ```bash
   python main.py --config_file path/to/your_config.yaml
   ```
   Optional arguments:
   - `--current_iteration`: Start from a specific iteration (default: 0)
   - `--email`: Email for job notifications (default: system username)

4. **Monitor progress:**
   Output and logs are written to the `work_directory` specified in your config.

---

## Directory Structure

- `main.py` — Entry point for the optimization loop
- `postprocessing.py` — Handles result evaluation and scoring
- `bayesian_optimization/utils.py` — Utility functions for file handling, parameter updates, etc.
- `bayesian_optimization/optimizer.py` — Scoring and optimizer logic
- `runscripts/` — Example SLURM or shell scripts for running simulations and postprocessing
- `config_new.yaml` — Example configuration file

---

## Extending and Customization

- **Targets:**
  You can define new targets or scoring functions by editing `optimizer.py`.
- **Model Support:**
  While designed for Bern3D, the modular structure allows adaptation to other models with similar input/output conventions.
- **Job Submission:**
  The `submit_job` utility can be adapted for different schedulers or local runs.

---

## Troubleshooting

- **Missing files or directories:**
  Ensure all paths in your config file exist and are accessible.
- **Job failures:**
  Check the SLURM or shell script logs in your `work_directory`.
- **Parameter errors:**
  Make sure parameter names and bounds in your config match those in your model's parameter files.
- **Other errors:**
  Currently, Bern3D_v3 is not supported
---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## Acknowledgements

This code is adapted from [Pierre Testorf's repository](https://gitlab.climate.unibe.ch/pierre.testorf/bayesian_optimization).
