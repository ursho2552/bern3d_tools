#!/bin/bash
#SBATCH --mail-type=end,fail
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --output="postprocessing.out"
#SBATCH --error="postprocessing.out"

module purge
module load Anaconda3
eval "$(conda shell.bash hook)"

PYTHON=py3_bern_tools

conda activate $PYTHON

python $SLURM_JOB_NAME --config_file $1 --simulation_name $2
