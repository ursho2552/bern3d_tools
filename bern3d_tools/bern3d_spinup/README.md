# Bern3D Spinup Module

This module provides a framework for performing multi-phase spinup of the Bern3D model. It automates the process of setting up, configuring, and submitting sequential spinup jobs, each with its own configuration and dependencies.

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

This module automates the multi-phase spinup process for the Bern3D model. Each spinup phase can have its own parameter overrides and job script, and jobs are submitted with dependencies to ensure correct sequencing.

**Key features:**
- Automated setup of run directories and parameter files for each spinup phase
- Phase-specific parameter overrides
- Sequential job submission with dependencies (using SLURM)
- Flexible configuration via YAML files

---

## How It Works

1. **Configuration:**
   You provide a YAML configuration file specifying paths, executable names, spinup phases, and job scripts.

2. **Setup:**
   For each spinup phase, the module:
   - Copies the template executable and parameter files
   - Applies phase-specific parameter overrides

3. **Job Submission:**
   Each phase is submitted as a job, with dependencies ensuring that phase N+1 starts only after phase N completes.

---

## Installation

Clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd bern3d_tools/bern3d_spinup
```

---

## Configuration

All settings are controlled via a YAML configuration file. See `config_files/spinup_NPZD.yaml` for an example.

**Key fields:**
- `bern3d_template`: Path to the Bern3D template directory (should contain the executable and parameter files)
- `bern3d_executable_name`: Name of the Bern3D executable
- `bern3d_restart_files`: Path to restart files (or `!!python/none`)
- `work_directory`: Directory for all outputs and temporary files
- `result_directory`: Directory where to copy the results after finishing (or `!!python/none`)
- `python_submit_script`: SLURM script to run a python script with command line arguments
- `sbatch_script`: Dictionary mapping each phase to its SLURM or shell script
- `time`: Maximum allowed run time for each job
- `spinup_phases`: Total number of spinup phases to run (e.g., 3)
- `current_phase`: Phase to start from (e.g., 1)

**Example:**
```yaml
bern3d_template: "/path/to/bern3d_f90/run"
bern3d_executable_name: "RUNNAME"
bern3d_restart_files: !!python/none
work_directory: "/path/to/spinup"
result_directory: !!python/none
python_submit_script: "runscripts/run_python_script.sh"
sbatch_script:
  phase1: "runscripts/run_bern3d_f90_phase1.sh"
  phase2: "runscripts/run_bern3d_f90_phase2.sh"
  phase3: "runscripts/run_bern3d_f90_phase3.sh"
time: "06:00:00"
spinup_phases: 3
current_phase: 1
```

Parameter overrides for each phase are defined in `spinup/override.py`. This is done by first applying the overrides of each phase sequentially, i.e., in Spinup 3 the overrides of phase 1 and 2 are done before the overrides of phase 3 are done.

---

## Usage

1. **Prepare your configuration file**
   Edit a copy of `config_files/spinup_NPZD.yaml` to match your system and spinup setup.

2. **Ensure your template directory is ready**
   The `bern3d_template` directory should contain all files needed to run a Bern3D simulation.

3. **Run the spinup workflow:**
   ```bash
   python main.py --config_file ./config_files/spinup_NPZD.yaml --email your@email.com
   ```
   - The script will submit jobs for each spinup phase, with dependencies to ensure correct order.

---

## Directory Structure

- `main.py` — Entry point for the spinup workflow and job management
- `spinup/utils.py` — Utility functions for configuration checking and setup
- `spinup/override.py` — Parameter overrides for each spinup phase
- `config_files/` — Example configuration files
- `runscripts/` — Example SLURM or shell scripts for running each phase

---

## Extending and Customization

- **Spinup Phases:**
  Add or modify phases and their overrides in `spinup/override.py` and your config YAML.
- **Job Submission:**
  The `submit_job` utility can be adapted for different schedulers or local runs.
- **Parameter Overrides:**
  Easily extend the override dictionary for new phases or custom spinup sequences.

---

## Troubleshooting

- **Missing files or directories:**
  Ensure all paths in your config file exist and are accessible.
- **Job failures:**
  Check the SLURM or shell script logs in your `work_directory`.
- **Parameter errors:**
  Make sure parameter names in your overrides match those in your model's parameter files.
- **Phase errors:**
  Ensure `spinup_phases` and `current_phase` are set correctly and that scripts exist for each phase.

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---