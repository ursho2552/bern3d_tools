# Bern3D Sensitivity Analysis Module
This module is designed to perform comprehensive sensitivity analysis for the Bern3D Model. It systematically varies model parameters to quantify their impact on key variables, providing insights into model behavior and parameter importance.

## Features
- Automated Parameter Variation: Systematically creates high and low parameter variations based on configurable relative changes.
- Parallel Job Submission: Submits multiple sensitivity runs using SLURM with configurable parameters and dependencies.
- Reference Run Generation: Automatically creates a baseline reference run for comparison.
- Comprehensive Analysis: Compares sensitivity runs against reference to quantify parameter impacts.
- Flexible Configuration: Uses YAML configuration files to define parameters, paths, and analysis settings.
- Robust Error Handling: Tracks failed runs and handles missing output files gracefully.
- Statistical Metrics: Calculates multiple sensitivity metrics including relative differences, spatial statistics, and rankings.

## File Structure

The module consists of the following key components:

**Core Scripts**
- `main.py`: Main entry point for both running sensitivity experiments and analyzing results.
- `sensitivity/`: Directory containing core functionality
    - `utils.py`: Utility functions for configuration validation, file parsing, and directory setup.
    - `evaluation.py`: Analysis functions for processing sensitivity results and calcualting metrics
    - `__init__.py`: Package initialization importing all analysis functions.

**Configuration**
- `sensitivity_setup.yaml`: Main configuration file specifying:
    - Model paths and executable names.
    - Parameter lists for sensitivity analysis.
    - Target variables and output files.
    - SLURM script paths and timing settings.

**SLURM Scripts**
- `runscripts/run_bern3d_f90_sequential.sh`: SLURM script for executing Bern3D model runs
- `runscripts/run_evaluation.sh`: SLURM script for post-processing and analysis jobs

Other example SLURM scripts for executing Bern3D in parallel with three or four heterogeneous jobs are also provided.

## Configuration
To use the sensitivity module, you mainly need to customize the entries of the `sensitivity_setup.yaml` file to fit your sensitivity analysis. You may also change the SLURM scripts for changing how the model is run, or the python environment.

## Usage
Run the following command
```bash
python main.py --configuration_name config_files/sensitivity_setup.yaml --email your.email@domain.com
```

This will:
- Create a reference run with original parameters
- Generate high (+X%) and low (-X%) variations for each parameter
- Submit all jobs to SLURM with proper dependencies
- Schedule an analysis job to run after all simulations complete

In case you want to only analyze the results you can use the following:
```bash
python main.py --configuration_name config_files/sensitivity_setup.yaml --analyze_runs
```

## Output files
The module generates several output files in the work directory:
- `sensitivity_analysis_results.csv`: Detailed results for all runs
- `sensitivity_summary.csv`: Aggregated statistics by parameter
- `run/`: Directory containing all model executables and input files
- `results/`: Directory containing all model output files

## Parameter Requirements

Parameters must be:

- Present in the model parameter file
- Numeric (integer or float values)
- Non-zero (for relative change calculations)
- Properly formatted in the configuration file
