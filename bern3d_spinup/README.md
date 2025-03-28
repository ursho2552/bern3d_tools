# Bern3D Spinup Module

The `bern3d_spinup` module automates the spinup process for the Bern3D climate model. It allows users to configure and execute multiple spinup phases (1, 2, or 3) with dependencies between phases. Each phase can have its own configuration and SLURM script, ensuring flexibility and modularity.

## Features

- **Multi-phase Spinup:** Supports up to 3 spinup phases, each with its own configuration and SLURM script.
- **Dynamic Directory Creation:** Automatically creates run directories for each spinup phase and copies the necessary template files.
- **Configuration Management:** Reads configuration files in YAML format and validates paths and parameters.
- **SLURM Job Submission:** Submits jobs for each spinup phase with optional dependencies between phases.

---

## Directory Structure

```plaintext
bern3d_spinup/
├── main.py                   # Main script to initialize and run the spinup process
├── spinup/
│   ├── utils.py               # Utility functions for configuration, directory creation, and job submission
│   └── __init__.py             # Module initialization
├── config_files/
│   ├── spinup_setup.yaml      # Main configuration file for the spinup process
│   ├── spinup_phase1.yaml      # Configuration for spinup phase 1
│   ├── spinup_phase2.yaml      # Configuration for spinup phase 2
│   └── spinup_phase3.yaml      # Configuration for spinup phase 3
├── runscripts/
│   ├── run_bern3d_f90_phase1.sh # SLURM script for spinup phase 1
│   ├── run_bern3d_f90_phase2.sh  # SLURM script for spinup phase 2
│   └── run_bern3d_f90_phase3.sh  # SLURM script for spinup phase 3
```
