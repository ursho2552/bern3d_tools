#!/bin/bash
#SBATCH --mail-user=name.lastname@unibe.ch
#SBATCH --mail-type=end,fail
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --output="optimizer.out"
#SBATCH --error="optimizer.out"

module purge
module load Anaconda3
eval "$(conda shell.bash hook)"

PYTHON=py3_bayesian

conda activate $PYTHON

python $SLURM_JOB_NAME --configuration_name $1 --current_iteration $2
