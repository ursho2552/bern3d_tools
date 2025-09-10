# Sensitivity Analysis Module

This module provides a framework for performing **sensitivity analysis** of model parameters, specifically designed for use with the Bern3D model. It automates the process of running model simulations with perturbed parameters, evaluating the impact on model outputs, and summarizing the results.

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

---

## Overview

This module automates the process of sensitivity analysis for Bern3D model parameters. It systematically perturbs selected parameters (using relative changes), runs the model, and evaluates the effect on specified output fields.

**Key features:**
- Automated job submission and management (supports SLURM job scripts)
- Flexible configuration via YAML files
- Supports both single and multiple parameter perturbations
- Automated evaluation and summary of sensitivity results

---

## How It Works

1. **Configuration:**
   You provide a YAML configuration file specifying paths, parameters to perturb, relative change values, and output fields to analyze.

2. **Setup:**
   For each parameter, the module:
   - Creates new run directories and parameter files for "Low" and "High" perturbations (decrease/increase by the specified relative change).
   - Copies necessary model files and restart files.

3. **Simulation:**
   Each perturbed setup is submitted as a job to the cluster.

4. **Evaluation:**
   After all simulations finish, the module:
   - Collects model outputs for each run and the reference.
   - Compares perturbed runs to the reference for each target field.
   - Computes sensitivity metrics (mean, absolute/relative differences, etc.).

5. **Results:**
   Results are saved as CSV files for further analysis.

---

## Installation

To use this module, clone the repository and install the required dependencies

```bash
git clone <repository-url>
cd bern3d_tools/bern3d_sensitivity
```
---

## Configuration

All settings are controlled via a YAML configuration file. See `config_files/sensitivity_setup.yaml` for an example.

**Key fields:**
- `bern3d_template`: Path to the Bern3D template directory (should contain the executable and parameter files)
- `bern3d_executable_name`: Name of the Bern3D executable
- `bern3d_parameter_file`: Name of the parameter file to modify
- `bern3d_restart_files`: Path (with wildcards allowed) to restart files
- `parameter_list`: Dictionary of parameters to perturb and their relative change (e.g., `0.1` for ±10%)
- `relative_change`: Default relative change to use if not specified for a parameter
- `target_field`: Dictionary mapping output variable names to NetCDF file suffixes
- `work_directory`: Directory for all outputs and temporary files
- `bern3d_run_script`: Path to the SLURM or shell script for running the model
- `evaluation_script`: Path to the script for evaluating results
- `time_bern3d`, `time_evaluation`: Maximum allowed run times for jobs

**Example:**
```yaml
bern3d_template: "/path/to/bern3d_f90/run"
bern3d_executable_name: "RUNNAME"
bern3d_parameter_file: ".bgc.parameter"
bern3d_restart_files: "/path/to/results/Spinup2*"

parameter_list:
  ligtot: 0.1
  freefemax: 0.4
  kscavcons: 0.7

relative_change: 0.25

target_field:
  Fe: ".00001765_full_ave.nc"

work_directory: "/path/to/sensitivity_analysis/"
bern3d_run_script: "/path/to/run_bern3d_f90_sequential.sh"
evaluation_script: "/path/to/run_evaluation.sh"
main_script_path: "/path/to/bern3d_sensitivity/"
time_bern3d: "10:00:00"
time_evaluation: "01:00:00"
```

---

## Usage

1. **Prepare your configuration file**
   Edit a copy of `sensitivity_setup.yaml` to match your system, model, and analysis goals.

2. **Ensure your template directory is ready**
   The `bern3d_template` directory should contain all files needed to run a Bern3D simulation.

3. **Run the sensitivity analysis:**
   ```bash
   python main.py --configuration_name config_files/sensitivity_setup.yaml
   ```
   Optional arguments:
   - `--email`: Email address for job notifications (default: system username)
   - `--analyze_runs`: Analyze results after simulations finish (set this flag to skip job creation and only analyze)

4. **Monitor progress:**
   Output and logs are written to the `work_directory` specified in your config.

5. **Analyze results:**
   After all jobs finish, run:
   ```bash
   python main.py --configuration_name config_files/sensitivity_setup.yaml --analyze_runs
   ```
   This will generate CSV files summarizing the sensitivity results.

---

## Directory Structure

- `main.py` — Entry point for the sensitivity analysis workflow
- `sensitivity/utils.py` — Utility functions for file handling, parameter updates, etc.
- `sensitivity/evaluation.py` — Evaluation and summary of sensitivity results
- `config_files/` — Example configuration files
- `runscripts/` — Example SLURM or shell scripts for running simulations and evaluation

---

## Extending and Customization

- **Target Fields:**
  You can add or change output variables to analyze by editing the `target_field` section in your config.
- **Parameter Selection:**
  Add or remove parameters in `parameter_list` to control which parameters are perturbed.
- **Job Submission:**
  The `submit_job` utility can be adapted for different schedulers or local runs.
- **Evaluation:**
  You can extend `evaluation.py` to compute additional metrics or handle new output formats.

---

## Troubleshooting

- **Missing files or directories:**
  Ensure all paths in your config file exist and are accessible.
- **Job failures:**
  Check the SLURM or shell script logs in your `work_directory`.
- **Parameter errors:**
  Make sure parameter names in your config match those in your model's parameter files and are numeric and non-zero
- **Output errors:**
  Ensure the output NetCDF files contain the variables specified in `target_field`.

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---
