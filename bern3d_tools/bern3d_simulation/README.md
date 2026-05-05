# Bern3D Simulation Module

This module provides a framework for running Bern3D model simulations with robust job management. It is designed to automatically handle job submission, monitor simulation status, and restart simulations in case of timeouts or crashes.

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

This module automates the process of running a Bern3D simulation, including:
- Setting up the run directory and copying necessary files
- Submitting the simulation job to a cluster (e.g., via SLURM)
- Monitoring the simulation output for successful completion
- Automatically restarting the simulation if it fails or times out

---

## How It Works

1. **Configuration:**
   You provide a YAML configuration file specifying paths, executable names, scripts, and run settings.

2. **Initial Submission:**
   The module sets up the run directory, copies the necessary files, and submits the simulation job.

3. **Monitoring:**
   After the job finishes, the module checks the output log for a success message.

4. **Restarting:**
   If the simulation did not finish successfully, the module automatically resubmits the job until completion.

---

## Installation

Clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd bern3d_tools/bern3d_simulation
```
---

## Configuration

All settings are controlled via a YAML configuration file. See `config_files/config.yaml` for an example.

**Key fields:**
- `bern3d_template`: Path to the Bern3D template directory (should contain the executable and parameter files)
- `bern3d_executable_name`: Name of the Bern3D executable
- `bern3d_restart_files`: Path (with wildcards allowed) to restart files
- `work_directory`: Directory for all outputs and temporary files
- `simulation_name`: Name for this simulation run
- `bern3d_submit_script`: Path to the SLURM or shell script for running the model
- `python_script`: Path to the script for checking/restarting the simulation
- `main_script`: Path to the main script directory
- `time_bern3d`, `time_python`: Maximum allowed run times for jobs
- `config_file`: Path to this configuration file

**Example:**
```yaml
bern3d_template: /path/to/bern3d_f90/run
bern3d_executable_name: RUNNAME
bern3d_restart_files: "/path/to/results/Spinup2*"
work_directory: "/path/to/test_restart/"
simulation_name: "restart_test"
bern3d_submit_script: "/path/to/run_bern3d.sh"
python_script: "/path/to/run_simulation_check.sh"
main_script: "/path/to/bern3d_simulation/"
time_bern3d: "00:30:00"
time_python: "00:05:00"
config_file: "/path/to/config.yaml"
```

---

## Usage

1. **Prepare your configuration file**
   Edit a copy of `config_files/config.yaml` to match your system and simulation setup.

2. **Ensure your template directory is ready**
   The `bern3d_template` directory should contain all files needed to run a Bern3D simulation.

3. **Run the simulation:**
   ```bash
   python main.py --config_file ./config_files/config.yaml --initial_submission
   ```
   - The `--initial_submission` flag indicates this is the first submission.
   - The script will handle restarts automatically if the simulation does not finish successfully.

   If the simulation times out or crashes, the script should automatically restart it. However, you can also do this manually by running:
    ```python
    python main.py --config_file ./config_files/config.yaml --restart
    ```

4. **Email notifications:**
   You can provide an email address for job notifications:
   ```bash
   python main.py --config_file ./config_files/config.yaml --initial_submission --email your@email.com
   ```

---

## Directory Structure

- `main.py` — Entry point for the simulation workflow and job management
- `simulation/utils.py` — Utility functions for configuration checking and simulation status
- `config_files/` — Example configuration files
- `runscripts/` — Example SLURM or shell scripts for running simulations

---

## Extending and Customization

- **Job Submission:**
  The `submit_job` utility can be adapted for different schedulers or local runs.
- **Simulation Monitoring:**
  You can modify the success string or add more robust error handling in `utils.py`.
- **Restart Logic:**
  The restart logic can be extended to handle more complex workflows or dependencies.

---

## Troubleshooting

- **Missing files or directories:**
  Ensure all paths in your config file exist and are accessible.
- **Job failures:**
  Check the SLURM or shell script logs in your `work_directory`.
- **Parameter errors:**
  Make sure parameter names in your config match those in your model's parameter files.
- **Output errors:**
  Ensure the output log file contains the expected success string.

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---
