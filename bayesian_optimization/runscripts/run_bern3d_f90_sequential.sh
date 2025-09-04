#!/bin/bash
#SBATCH --mail-type=end,fail
#SBATCH --output="%x.out"
#SBATCH --error="%x.out"
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --mem=2G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

# Load modules
module load intel/2023a
module load netCDF/4.9.2-iimpi-2023a
module load netCDF-Fortran/4.6.1-iimpi-2023a
module load CMake/3.26.3-GCCcore-12.3.0

ulimit -s unlimited
export OMP_STACKSIZE=32M
export OMP_PROC_BIND=close
export I_MPI_COMPATIBILITY=4
export HDF5_USE_FILE_LOCKING=FALSE

# Run in serial mode
srun ./$SLURM_JOB_NAME > $SLURM_JOB_NAME.out 2>&1