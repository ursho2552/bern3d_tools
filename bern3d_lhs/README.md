# Latin Hypercube Sampling Module

This module provides a framework for performing a **latin hypercube sampling** designed for Bern3D. It automates the process of running model simulations with a different set of parameters specified by the user.

---

## Table of Contents

---

## Overview

This module automates the latin hypercube sampling for Bern3D. It creates the sampling matrix based on paramter boundaries provided, changes the values in the parameter files, and runs the simulations. To avoid overloading the cluster, this module schedules jobs in batches, where the batch size can be set by the user.

**Key features:**
- Automated job submission and management (supports SLURM job scripts)
- Flexible configuration via YAML files
- Supports both single and multiple parameter perturbations

---

## How It Works

1. **Configuration:**
   You provide a YAML configuration file specifying paths, parameters to test, and the number of samples to generate.

2. **Setup:**
   For each parameter, the module:
   - Creates new executables and parameter files for each sample.
   - Copies necessary model files and restart files.

3. **Simulation:**
    Each setup is submitted as a job to the cluster in batches.

---

## Installation

To use this module, clone the repository and install the required dependencies

```bash
git clone <repository-url>
cd bern3d_tools/bern3d_sensitivity
```

---

## Configuration

All settings are controlled via a YAML configuration file. See `config_files/lhs_setup.yaml` for an example.

**Key fields:**
- `bern3d_template`: Path to the Bern3D template directory (should contain the executable and parameter files)
- `bern3d_executable_name`: Name of the Bern3D executable
- `bern3d_parameter_file`: Name of the parameter file to modify
- `bern3d_restart_files`: Restart files to use for the new runs (if needed)
- `parameter_list`: List of parameters to include in the sampling (with their boundaries)
- `num_concurrent_jobs`: Number of jobs to submit in each batch
- `num_samples`: Total number of samples to generate
- `work_dir`: Directory where the new runs will be created
- `bern3d_run_script`: Path to the SLURM job script template to use for running the simulations
- `main_script_path`: Path to the main script that will be executed for each run (if different from the run script)
- `time_bern3d`: Time to run each Bern3D simulation (used for job scheduling)

**Example:**
```yaml
bern3d_template: "/storage/scratch/users/uh24x373/Particle_flux/run"
bern3d_executable_name: "Spinup3"
bern3d_parameter_file: ".bgc.parameter"
bern3d_restart_files: "/storage/scratch/users/uh24x373/Particle_flux/results/Spinup2*"
parameter_list:
  k_POC: [1.5e-6, 4.0e-6]
  SinkVel_scale: [0.5, 1.5]
  phi_lg: [0.85, 0.98]
  aE: [0.05, 0.25]
  sig1: [0.001, 0.015]
  sig2: [0.0001, 0.005]
  alphadenit: [-0.8, -0.01]
  Tref: [10.0, 20.0]

num_concurrent_jobs: 20
num_samples: 120

work_directory: "/storage/scratch/users/uh24x373/lhs_particle_flux/"
bern3d_run_script: "/storage/homefs/uh24x373/bgc_bern/bern3d_tools/shared/runscripts/run_bern3d_f90_mpi_4het.sh"
main_script_path: "/storage/homefs/uh24x373/bgc_bern/bern3d_tools/bern3d_lhs/"
time_bern3d: "24:00:00"
```

---

## Usage

1. **Prepare Configuration:**
   Create a YAML configuration file based on the example provided.

2. **Ensure your template directory is ready:**
   The `bern3d_template` directory should contain all files needed to run a Bern3D simulation.

3. **Run the LHS sampling:**
    ```bash
    python main.py --config_file=config_files/lhs_setup.yaml
    ```
    Optional arguments:
   - `--email`: Email address for job notifications (default: system username)

4. **Monitor progress:**
   Output and logs are written to the `work_directory` specified in your config.

---

## Directory Structure

- `main.py`: Main script to execute the LHS sampling
- `config_files/lhs_setup.yaml`: Example configuration file for LHS sampling
- `latin_hypercube_sampling/utils.py`: Utility functions for file handling, job submission, etc.
- `latin_hypercube_sampling/samples.py`: Functions for generating the LHS samples

---

## Extending and Customization

- **Parameter Selection:**
  Add or remove parameters in `parameter_list` to control which parameters are perturbed.
- **Job Submission:**
  The `submit_job` utility can be adapted for different schedulers or local runs.

  ---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---