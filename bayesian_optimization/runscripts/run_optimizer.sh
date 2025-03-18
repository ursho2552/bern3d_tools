#!/bin/bash
#SBATCH --mail-user=name.lastname@unibe.ch
#SBATCH --mail-type=end,fail
#SBATCH --cpus-per-task=1 --ntasks=1
#SBATCH --partition=icpu-poeppelmeier
#SBATCH --qos=job_icpu-poeppelmeier
#SBATCH --output="%x.out"
#SBATCH --error="%x.out"

module purge
module load Anaconda3
eval "$(conda shell.bash hook)"

PYTHON=py3_ubelix

conda activate $PYTHON

python ./$SLURM_JOB_NAME --configuration_name $1 --current_iteration $2
