#!/bin/bash
#SBATCH --mail-user=name.lastname@unibe.ch
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
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier

# Atmosphere task
#SBATCH hetjob
#SBATCH --cpus-per-task=1 --mem-per-cpu=2g --ntasks=1
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

#SBATCH --output="%x.out"
#SBATCH --error="%x.out"

# Load modules
module load intel/2023a
module load netCDF/4.9.2-iimpi-2023a
module load netCDF-Fortran/4.6.1-iimpi-2023a
module load CMake/3.26.3-GCCcore-12.3.0

ulimit -s unlimited
export OMP_STACKSIZE=32M
export OMP_PROC_BIND=close
export I_MPI_COMPATIBILITY=4

srun --het-group=0 --partition=epyc2 --ntasks=1 --cpus-per-task=1 --export=all ./$SLURM_JOB_NAME : \
--het-group=1 --partition=icpu-poeppelmeier --ntasks=1 --cpus-per-task=6 --export=all ./$SLURM_JOB_NAME : \
--het-group=2 --partition=epyc2 --ntasks=1 --cpus-per-task=1 --export=all ./$SLURM_JOB_NAME > $SLURM_JOB_NAME.out 2>&1

ERR=$?
echo "Error code: $ERR"
exit $ERR