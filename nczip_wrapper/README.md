# NCZIP Wrapper

This repository contains scripts to compress NetCDF files using the `nczip` script and verify the compression using the `ncequal` script. The compression process is managed by a Python wrapper script that handles parallel processing and logging.

## Contents

- `nczip.sh`: Bash script to compress NetCDF files by converting them to NetCDF-4 if needed.
- `ncequal.py`: Python script to compare two NetCDF files for equality.
- `run_compression.py`: Python wrapper script to compress NetCDF files and verify the compression.
- `compress_output.sh`: SLURM job script to compress the contents of a directory.
- `test_submission.sh`: Template of a SLURM submission script for Bern3D and subsequent compression.

## Getting your python environment on UBELIX

In order to run the compression script, you need to setup your python environment on UBELIX. To this end you can follow these steps:

1. On the login node load the Anaconda module by running `module load Anaconda3`
2. Configure the current session to work propertly with conda by running: `eval "$(conda shell.bash hook)"`
3. Create your environment by running `conda env create -f requirements.yml`

The last step will create a conda environment called py3_ncwrapper, which you can use for running the compression scripts. You can test this environment by calling `conda activate py3_ncwrapper`.


## Running the Compression Script
To run the compression script, use the SLURM script `compress_output.sh`. This script sets up the environment, loads the necessary modules, and runs the compression script with the specified configuration.

In the `compress_output.sh` you need to change the paths and name of your python environment. Furthermore, you need to add the path to the compression script to your copy of the repository as:

```bash
COMPRESSION_SCRIPT=/storage/homefs/uh24x373/bgc_bern/nczip_wrapper/compress_output.sh
```

And run the compression at an appropriate time as:

```bash
sbatch $COMPRESSION_SCRIPT $WRKDIR/results
```

Note that you will have to setup your own python environment (see requiremnts.txt) and either define the nczip.sh and ncequal.py paths in compress_output.sh or provide them in the sbatch command as additional inputs:

```bash
sbatch $COMPRESSION_SCRIPT <input_directory> --nczip_script <path> --ncequal_script <path> --varnum <int>
```

## SLURM Job Script

A typical runscript for Bern3D would then look as follows:

```bash
#!/bin/bash
#SBATCH --job-name="RUNNAME"
#SBATCH --time=01:20:00
#SBATCH --mail-user=firstname.lastname@unibe.ch # Adjust to your email
#SBATCH --mail-type=end,fail

# Parallel run
######################################
# I/O task
#SBATCH --cpus-per-task=1 --mem-per-cpu=2g --ntasks=1
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

# Ocean task (OpenMP enabled)
#SBATCH hetjob
#SBATCH --cpus-per-task=6 --mem-per-cpu=1g --ntasks=1
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

# Atmosphere task
#SBATCH hetjob
#SBATCH --cpus-per-task=1 --mem-per-cpu=2g --ntasks=1
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

#SBATCH --output="%x.out"
#SBATCH --error="%x.out"

# Load modules
module purge
module load intel/2023a
module load netCDF/4.9.2-iimpi-2023a
module load netCDF-Fortran/4.6.1-iimpi-2023a
module load CMake/3.26.3-GCCcore-12.3.0
module list

# ====================================================================================
# CHANGE PATHS HERE
# ====================================================================================
# Define workdirectory
WORK_DIRECTORY=/storage/homefs/uh24x373/bgc_bern/bern3d_f90
EXECUTABLE="$WORK_DIRECTORY/run/$SLURM_JOB_NAME"
# Define compression script
COMPRESSION_SCRIPT=/storage/homefs/uh24x373/bgc_bern/nczip_wrapper/compress_output.sh
# ====================================================================================


ulimit -s unlimited
export OMP_STACKSIZE=32M
export OMP_PROC_BIND=close
export I_MPI_COMPATIBILITY=4
#export I_MPI_FABRICS=shm:ofi # Uncomment in case of slow MPI communication

# The following het-group options need to be the same as the ones in the SBATCH header (not documented in Slurm. BUG?)
srun --het-group=0 --ntasks=1 --cpus-per-task=1 --export=all $EXECUTABLE : \
     --het-group=1 --ntasks=1 --cpus-per-task=6 --export=all $EXECUTABLE : \
     --het-group=2 --ntasks=1 --cpus-per-task=1 --export=all $EXECUTABLE > $WORK_DIRECTORY/run/$SLURM_JOB_NAME.out 2>&1

ERR=$?

if [[ ${ERR} -eq 0 ]]
then
    # Run the compression
    sbatch $COMPRESSION_SCRIPT $WORK_DIRECTORY/results/
else
    echo "Error in the simulation"
fi

```

## Script Descriptions

```nczip.sh```

The ```nczip.sh``` script compresses NetCDF files by converting them to NetCDF-4 if needed. It supports various options for compression levels, chunking policies, and more. Note that the compressed and original files can be kept.

```ncequal.py```

The ```ncequal.py``` script compares two NetCDF files for equality. It checks whether the files contain the same variables and whether the variables have the same values at randomly selected time steps.

```run_compression.py```

The ```run_compression.py``` script is a Python wrapper that compresses NetCDF files using the nczip script and verifies the compression using the ncequal script. It processes files in parallel and logs the results.
This script performs a walk to find all NetCDF files in the subdirectories of the provided input directory.

## Dependencies

See requirements.yml for python packages and test_submission.sh for modules needed to run on UBELIX

## Notes

The code in this repository is based on https://gitlab.climate.unibe.ch/burger/nczip_wrapper
