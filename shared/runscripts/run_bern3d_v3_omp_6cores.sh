#!/bin/bash
#SBATCH --mail-type=end,fail
#SBATCH --account=invest
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem=2G
#SBATCH --cpus-per-task=6
#SBATCH --output="%x.out"
#SBATCH --error="%x.out"

# Load modules
module load GCCcore/12.3.0
module load intel-compilers/2023.1.0
module load impi/2021.9.0-intel-compilers-2023.1.0
module load iimpi/2023a
module load netCDF/4.9.2-iimpi-2023a
module load netCDF-Fortran/4.6.1-iimpi-2023a
module load Workspace_Home
module load imkl-FFTW/2023.1.0-iimpi-2023a
module load intel/2023a
module load Workspace/2.1

ulimit -s unlimited
export OMP_STACKSIZE=32M
export OMP_PROC_BIND=close
export HDF5_USE_FILE_LOCKING=FALSE

./$SLURM_JOB_NAME $SLURM_JOB_NAME

ERR=$?
echo "Error code: $ERR"
exit $ERR
