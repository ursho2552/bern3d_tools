# Shared Utilities Module

This module provides utility functions used across the `bern3d_tools` package. These functions support configuration management, job submission, file handling, and parameter manipulation for all Bern3D workflows (simulation, sensitivity, spinup, and optimization).

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Key Functions](#key-functions)
- [Usage](#usage)
- [Extending and Customization](#extending-and-customization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

The shared utils module centralizes common functionality needed by all Bern3D modules. This avoids code duplication and ensures consistent behavior for tasks like reading configuration files, submitting jobs, copying templates, and editing parameter files.

---

## How It Works

- **Configuration Management:**
  Read YAML configuration files and populate dataclass objects for type-safe access.
- **Job Submission:**
  Submit jobs to SLURM (or other schedulers) with support for dependencies and custom arguments.
- **File Handling:**
  Copy template files, set up run directories, and manage restart files.
- **Parameter Manipulation:**
  Parse parameter files to dictionaries, infer types, adapt parameter values, and write new parameter files.

---

## Installation

The shared utils module is included as part of the `bern3d_tools` package.
To use it in your scripts, simply import:

```python
import bern3d_tools.shared.utils as shared_utils
```

---

## Key Functions

- **get_user_email()**
  Returns the user's email address for job notifications.

- **read_config_file(config_file, config_class)**
  Reads a YAML configuration file and returns a populated dataclass.

- **submit_job(...)**
  Submits a job using `sbatch`, with support for dependencies, custom job names, and command-line arguments.

- **copy_template_files(exec_name, new_name, template_dir, work_dir)**
  Copies only the necessary model files for a specific executable, renaming as needed.

- **setup_run_directory(template_dir, executable_name, new_name, work_dir, restart_files)**
  Sets up a run directory, copies template and restart files, and returns the run directory path.

- **parse_to_dict(file_path, reset=False)**
  Parses a parameter file into a Python dictionary, inferring types.

- **infer_type(value, reset=False)**
  Infers the type (bool, int, float, str) from a string value.

- **adapt_dictionary(config_dict, parameter, factor, new_value=None)**
  Adapts parameter values in a configuration dictionary, supporting relative or absolute changes.

- **create_new_parameter_file(config_dict, parameter_file_name)**
  Writes a configuration dictionary to a new parameter file.

### Shared Runscripts

The `runscripts/` directory contains pre-configured SLURM scripts for different Bern3D execution modes:

- **run_bern3d_f90_omp_8cores.sh** — OpenMP execution on 8 cores
- **run_bern3d_f90_mpi_3het.sh** — MPI execution with 3 heterogeneous tasks (I/O, Ocean, Atmosphere)
- **run_bern3d_f90_mpi_4het.sh** — MPI execution with 4 heterogeneous tasks (adds Biogeochemistry)
- **run_bern3d_f90_mpi_5het.sh** — MPI execution with 5 heterogeneous tasks (adds Sediment)
- **run_bern3d_f90_mpi_6het.sh** — MPI execution with 6 heterogeneous tasks (adds Ice-sheet/CISM)
- **run_bern3d_v3_omp_6cores.sh** — Bern3D-v3 execution on 6 cores

These scripts handle module loading, environment variables, and proper SLURM configuration for the University of Bern cluster environment.

---

## Usage

Import the module in your workflow:

```python
import bern3d_tools.shared.utils as shared_utils

# Example: Read config and submit a job
config = shared_utils.read_config_file("config.yaml", MyConfigClass)
job_id = shared_utils.submit_job(
    script_template="run_bern3d.sh",
    executable_name="RUNNAME",
    executable_path="/path/to/run",
    time="06:00:00"
)
```

---

## Extending and Customization

- **Job Submission:**
  Adapt `submit_job` for other schedulers or add new dependency types as needed.
- **Parameter Parsing:**
  Extend `parse_to_dict` and `adapt_dictionary` to support new parameter file formats or value types.
- **File Handling:**
  Add new utilities for archiving, logging, or advanced file management.

---

## Troubleshooting

- **File Not Found:**
  Ensure all paths provided to functions exist and are accessible.
- **Job Submission Errors:**
  Check SLURM output and ensure your scripts and permissions are correct.
- **Parameter Parsing Issues:**
  Make sure your parameter files follow the expected format (key = value).

---

## Contributing

Contributions are welcome! Please open issues or submit pull requests for bug fixes, new features, or documentation improvements.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.