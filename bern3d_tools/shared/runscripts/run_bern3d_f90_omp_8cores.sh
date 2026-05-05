#!/bin/bash
#SBATCH --mail-type=end,fail
#SBATCH --output="%x.out"
#SBATCH --error="%x.out"
#SBATCH --account=invest
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --nodes=1
#SBATCH --mem=2G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8

##SBATCH --job-name=Reference
##SBATCH --chdir=/storage/scratch/users/uh24x373/Optimization_wind_test_new/run
##SBATCH --mail-user=uh24x373@campus.unibe.ch


# Load modules
module load intel/2023a
module load netCDF/4.9.2-iimpi-2023a
module load netCDF-Fortran/4.6.1-iimpi-2023a
module load CMake/3.26.3-GCCcore-12.3.0

ulimit -s unlimited
unset SLURM_MEM_PER_CPU
unset SLURM_MEM_PER_GPU

export OMP_STACKSIZE=32M
export OMP_PROC_BIND=close
export I_MPI_COMPATIBILITY=4
export HDF5_USE_FILE_LOCKING=FALSE

# Run in serial mode
srun ./$SLURM_JOB_NAME > $SLURM_JOB_NAME.out 2>&1