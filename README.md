# bern3d_tools

A modular Python toolkit for running, managing, and analyzing Bern3D model simulations.
This repository provides a unified framework for simulation management, sensitivity analysis, Bayesian optimization, spinup workflows, and NetCDF compression, all tailored for Bern3D but adaptable to similar models.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Modules](#modules)
  - [Shared Utilities](#shared-utilities)
  - [Simulation Module](#simulation-module)
  - [Sensitivity Analysis Module](#sensitivity-analysis-module)
  - [Bayesian Optimization Module](#bayesian-optimization-module)
  - [Spinup Module](#spinup-module)
  - [NCZIP Wrapper](#nczip-wrapper)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Extending and Customization](#extending-and-customization)
- [License](#license)

---

## Overview

`bern3d_tools` is designed to automate and streamline the workflow around the Bern3D model.
It covers everything from launching and monitoring simulations (with automatic restarts), to parameter sensitivity analysis, Bayesian optimization, multi-phase spinup, and efficient NetCDF file compression.

All modules are built to be interoperable and share a common set of utility functions for configuration, job submission, and file handling.

---

## Repository Structure

```
bern3d_tools/
│
├── bayesian_optimization/   # Bayesian optimization of model parameters
├── bern3d_sensitivity/      # Sensitivity analysis of model parameters
├── bern3d_simulation/       # Robust simulation launching and monitoring
├── bern3d_spinup/           # Multi-phase spinup workflow
├── nczip_wrapper/           # NetCDF compression and verification tools
├── shared/                  # Shared utility functions (used by other modules)
└── README.md                # This file
```

---

## Modules

### Shared Utilities

- **Location:** `shared/`
- **Purpose:** Common functions for configuration management, job submission, file handling, and parameter manipulation.
- **Usage:** All other modules import and use these utilities for consistent workflows.

### Simulation Module

- **Location:** `bern3d_simulation/`
- **Purpose:** Launches Bern3D simulations, monitors progress, and automatically restarts jobs if they fail or time out.
- **Features:** Robust job management, restart logic, and easy integration with other modules.

### Sensitivity Analysis Module

- **Location:** `bern3d_sensitivity/`
- **Purpose:** Automates parameter sensitivity analysis by running perturbed simulations and evaluating their impact.
- **Features:** Batch job submission, automated evaluation, and summary of sensitivity metrics.

### Bayesian Optimization Module

- **Location:** `bayesian_optimization/`
- **Purpose:** Performs Bayesian optimization of model parameters to match observational targets.
- **Features:** Automated simulation setup, iterative optimization, and flexible configuration.

### Spinup Module

- **Location:** `bern3d_spinup/`
- **Purpose:** Manages multi-phase spinup workflows, with phase-specific parameter overrides and sequential job dependencies.
- **Features:** Automated setup and submission of sequential spinup jobs.

### NCZIP Wrapper

- **Location:** `nczip_wrapper/`
- **Purpose:** Compresses NetCDF files using `nczip` and verifies integrity with `ncequal`.
- **Features:** Parallel compression, SLURM integration, and validation of compressed files.

---

## Installation

The Bern3D Tools repository contains various tools and scripts for working with the Bern3D model. This repository is organized into different modules, each with its own specific functionality. To use the tools you will need to create your own pyhton environment. After cloning the repository, you can setup your python environment on UBELIX, by following these steps:

1. On the login node, load the Anaconda module by running `module load Anaconda3`
2. Configure the current session to work properly with conda by running: `eval "$(conda shell.bash hook)"`
3. Create your environment by running `conda env create -f requirements.yml`

The last step will create a conda environment called py3_bern_tools, which you can use for running all modules. You can test this environment by calling `conda activate py3_bern_tools`.


---

## Getting Started

1. **Choose a module** based on your workflow (simulation, sensitivity, optimization, spinup, or compression).
2. **Prepare a YAML configuration file** using the examples provided in each module’s `config_files/` directory.
3. **Run the main script** for your chosen module (see each module’s README for details).
4. **Monitor outputs and logs** in your specified work directories.

<!-- !All modules are designed to be interoperable. For example, the optimization and sensitivity modules use the simulation module to launch and monitor model runs. -->

---

## Extending and Customization

- All modules are modular and can be adapted for new workflows, schedulers, or models.
- Shared utilities can be extended for new file formats, job types, or parameter conventions.
- Contributions and improvements are welcome!

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---
