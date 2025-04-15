# Bayesian Optimization Module

This module provides functionality for performing Bayesian optimization, particularly in the context of climate modeling and simulation management. It includes various functions for data loading, parameter updates, and simulation management.

## Installation

To use this module, clone the repository and install the required dependencies

```bash
git clone <repository-url>
cd bern3d_tools/bayesian_optimization
```

## Usage

To use the Bayesian optimization module, adapt the config file to fit your simulation; see examples for Bern3D_F90 (config.yaml) and Bern3D_V3 (config_bern3d_v3.yaml).

Make sure that the `bern3d_template` directory only contains the compiled model and input files needed to run the model. You should be able to successfully run the model using only this directory. In case you are using Bern3D_V3, the parent directory should also contain the `input` directory with all the model contents needed before compilation. Furthermore, make sure all the files needed are present prior to running the optimizer (e.g., add the `missing.dat` file manually).

Next, on the terminal run

```
python main.py --configuration_name <path_to_your_config_file>
```

### Configuration file

This script uses a configuration file to setup the bayesian optimization. The configuration file needs to have the following fields:

``` bash
# Path to the configuration file
config_file_path: "path_to_config_file/my_config_file.yaml"

# The path to the scripts used to run the model, postprocessing and optimizer. These scripts are located in the runscripts directory
bern3d_script: "/bern3d_tools/bayesian_optimization/runscripts/run_bern3d_f90.sh"
postprocessing_script: "/bern3d_tools/bayesian_optimization/runscripts/run_postprocessing.sh"
optimizer_script: "/bern3d_tools/bayesian_optimization/runscripts/run_optimizer.sh"
python_scripts: "/bern3d_tools/bayesian_optimization/"

# The time limits for each of the scripts above in format (hh:mm:ss)
bern3d_script_time: "00:40:00"
postprocessing_script_time: "02:00:00"
optimizer_script_time: "00:10:00"

# Setup for optimization work directory
## Name of the optimization
simulation_name_bern3d: "Bay_test"
## Output to use in the comparison (timeseries or full)
output_type_bern3d: "timeseries"
## Output to use in the comparison (inst or ave)
output_timescale_bern3d: "ave"
## Path to work directory where all the simulation results will be stored (e.g. scratch)
work_directory: "/storage/scratch/users/my_username/Bayesian_optimizer/"
## Results directory of Bern3D and the optimizer, which will be in the workdirectory (will be overwritten during initialization)
output_files_bern3d: None
output_dir_optimizer: None

# Choose model to run
## For Bern3d-v3, the flag has to be set to False else Bern3d_F90 is used
bern3d_f90: True
## Name of the executable
template_name_bern3d: "RUNNAME"
## Path to the executable. Will be copied to work directory for execution
bern3d_template: "/storage/homefs/my_username/bgc_bern/bern3d_f90/run/"
## Path to restart file
initialization_file: "/storage/homefs/my_username/bgc_bern/bern3d-v3/results/Spi240_3__.00001765_full_inst.nc"

# Define data for comparison
## Path to the validation data
validation_data_path: "/storage/research/climate_climtip/my_username/data/"

# The number of iterations to run the Bayesian optimization algorithm
max_iterations: 3

# The name of the parameter file to change. It has to contain a keyword {my_simulation} which will be replaced by the simulation name
parameter_file: "{simulation_name_bern3d}.bgc.parameter"

# Parameters to be optimized (line number in the parameter file -  1)
parameter_mapping:
  sigmaPaPOC: 396
  sigmaPaCa: 397
  sigmaPaOp: 398
  sigmaPaDu: 399
  PaDesConst: 388
  pavelscale: 379
  bgcWterrPa: 383

# Limits of the parameters (should be tuples, hence we use !!python/tuple before the value)
parameter_bounds:
  sigmaPaPOC: !!python/tuple [0.,0.1]
  sigmaPaCa: !!python/tuple [0.,0.1]
  sigmaPaOp: !!python/tuple [0.,0.1]
  sigmaPaDu: !!python/tuple [0.,0.1]
  PaDesConst: !!python/tuple [1,10]
  pavelscale: !!python/tuple [0.03,0.16]
  bgcWterrPa: !!python/tuple [10000,25000]

# Settings for the optimizer
# Type of initialization
initialization_type: "lhs"
# Isotope of interest. Could be extended to use other variables
isotope: "Pad"
# Number of initializations
n_initialization: 10
# Surrogate type (GP currently not supported)
surrogate_type: "RF"
# Acquisition type
acquisition_type: "EI"
# Batch size
batchsize: 3
# Acquisition optimizer
acquisitition_optimizer: "auto"
# Job number
job_number: -1
```

## Testing

To run the tests for the module (work in progress), navigate to the project directory and execute:

```bash
pytest tests/
```

This will run all the unit tests defined in `test_bayesian_optimization.py` to ensure the functionality works as expected.

## Contributions

Contributions are welcome! Please feel free to submit a pull request or open an issue for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.

## Notes

The code in this repository was adapted from [**Pierre Testorf's repository**](https://gitlab.climate.unibe.ch/pierre.testorf/bayesian_optimization)
