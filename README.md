# Bern3D Tools

The Bern3D Tools repository contains various tools and scripts for working with the Bern3D climate model. This repository is organized into different components, each with its own specific functionality.

## Components

### Bayesian Optimization

The Bayesian Optimization module provides functionality for performing Bayesian optimization, particularly in the context of climate modeling and simulation management. It includes various functions for data loading, parameter updates, and simulation management.

#### Features
- Data loading and preprocessing
- Parameter updates
- Simulation management
- Bayesian optimization

#### Usage
To use the Bayesian optimization module, adapt the config file to fit your simulation; see examples for Bern3D_F90 (config_bern3d_f90.yaml) and Bern3D_V3 (config_bern3d_v3.yaml).

Next, on the terminal run:
```bash
python main.py --configuration_name <path_to_your_config_file>
```

For more details, refer to the [Bayesian Optimization README](https://gitlab.climate.unibe.ch/bern3d/bern3d_tools/-/blob/main/bayesian_optimization/README.md?ref_type=heads)

### NCZIP Wrapper

The NCZIP Wrapper module provides scripts for compressing NetCDF files using the NCZIP tool. It includes a bash script for setting up the environment and running the compression, as well as Python scripts for additional processing and validation.

#### Features
- Parallel compression of NetCDF files
- Validation of compressed files
- Customizable compression settings

#### Usage

To use the NCWIP wrapper, run the `compress_output.sh` script with the appropriate arguments:

```bash
./compress_output.sh <input_directory> [--nczip_script <path>] [--ncequal_script <path>] [--varnum <int>]
```

For more details, refer to the [NCZIP Wrapper README](https://gitlab.climate.unibe.ch/bern3d/bern3d_tools/-/blob/main/nczip_wrapper/README.md?ref_type=heads)

## Contributions
Contributions are welcome! Please feel free to submit a pull request or open an issue for any improvements, additions, or bug fixes.
