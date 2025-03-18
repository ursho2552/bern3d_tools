# Bayesian Optimization Module

This module provides functionality for performing Bayesian optimization, particularly in the context of climate modeling and simulation management. It includes various functions for data loading, parameter updates, and simulation management.

## Installation

To use this module, clone the repository and install the required dependencies

```bash
git clone <repository-url>
cd bern3d_tools/bayesian_optimization
```

### Getting your python environment on UBELIX

To setup your python environment on UBELIX, you can follow these steps:

1. On the login node load the Anaconda module by running `module load Anaconda3`
2. Configure the current session to work propertly with conda by running: `eval "$(conda shell.bash hook)"`
3. Create your environment by running `conda env create -f requirements.yml`

The last step will create a conda environment called py3_bayesian, which you can use for running the compression scripts. You can test this environment by calling `conda activate py3_bayesian`.


## Usage

To use the Bayesian optimization module, adapt the config file to fit your simulation; see examples for Bern3D_F90 (config.yaml) and Bern3D_V3 (config_bern3d_v3.yaml).

Next, on the terminal run

```
python main.py --configuration_name <path_to_your_config_file>
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
