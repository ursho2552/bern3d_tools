# Bern3D Simulation Restart Module

This module is designed to manage and restart simulations of the Bern3D model. It ensures that simulations are completed successfully, even in the case of timeouts or crashes. The module automates the submission of jobs, monitors their status, and handles dependencies between tasks.

## Features

- **Automated Job Submission**: Submits simulation jobs using SLURM with configurable parameters.
- **Simulation Monitoring**: Checks the status of simulations to ensure they complete successfully.
- **Restart Capability**: Automatically restarts simulations in case of failure or timeout.
- **Configurable Workflow**: Uses a YAML configuration file to define paths, scripts, and parameters.

---

## File Structure

The module consists of the following key files:

- **`main.py`**: The main script to launch and manage simulations.
- **`utils.py`**: Contains utility functions for job submission, directory creation, and status checking.
- **`run_bern3d.sh`**: SLURM script for running the Bern3D model.
- **`run_simulation_check.sh`**: SLURM script for running Python-based simulation checks.
- **`config.yaml`**: Configuration file specifying paths, scripts, and parameters.

---

## Usage
1. Edit the `config.yaml` file to specify the paths and parameters for your simulation
2. Submit the initial simulation using the following command
```python
python main.py --config_file ./config_files/config.yaml --initial_submission
```
3. Restart the simulation (if needed).

    If the simulation times out or crashes, the script should automatically restart it. You can also do this manually by running:
    ```python
    python main.py --config_file ./config_files/config.yaml --restart
    ```

## Workflow
1. Initial submission:
    - The `main.py` script reads the configuration file.
    - A new simulation directory is created using the template files.
    - The SLURM job is submitted using `run_bern3d.sh`.
2. Monitoring:
    - The script checks the simulation's output file for a success message (here `SIMULATION COMPLETE`).
    - If the simulation is incomplete, it is restarted.
3. Dependent job:
    - After the Bern3D simulation, a dependent Python job is submitted using `run_simulation_check.sh`.