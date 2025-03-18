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
