#!/bin/bash -l
#SBATCH --job-name=compress_output
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=name.lastname@unibe.ch
#SBATCH --time=00:15:00 # 15 minutes should be enough for most cases
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8 # 8 cores for parallel compression should be enough
#SBATCH --partition=epyc2
#SBATCH --qos=job_cpu

# Setup Environment in UBELIX
module purge
module load NCO
module load Anaconda3
eval "$(conda shell.bash hook)"

# ==============================================================================
# MAKE SURE TO ADJUST THE FOLLOWING VARIABLES ACCORDING TO YOUR SETUP
# ==============================================================================
# name of your conda environment (created with conda env create -f environment.yml)
PYTHON=py3_ncwrapper

# path to the python compression script from the repository
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPRESSION_SCRIPT="$SCRIPT_DIR/run_compression.py"
# path to the nczip.sh script from the repository
NCZIP_SCRIPT="$SCRIPT_DIR/nczip.sh"
# path to the ncequal.py script from the repository
NCEQUAL_SCRIPT="$SCRIPT_DIR/ncequal.py"
# number of random variables to test for equality
VARNUM=3
# ==============================================================================
# NO CHANGES NEEDED BELOW THIS LINE
# ==============================================================================

# Ensure at least one argument (config file) is provided
if [[ "$#" -lt 1 ]]; then
    echo "Usage: $0 <input_directory> [--nczip_script <path>] [--ncequal_script <path>] [--varnum <int>]"
    exit 1
fi

INPUT_DIRECTORY=$1
shift  # Shift arguments so that optional ones can be processed

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --nczip_script)
            NCZIP_SCRIPT="$2"
            shift 2
            ;;
        --ncequal_script)
            NCEQUAL_SCRIPT="$2"
            shift 2
            ;;
        --varnum)
            VARNUM="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#run the compression on test directory
conda activate $PYTHON
python $COMPRESSION_SCRIPT --input_directory "$INPUT_DIRECTORY" \
                           --nczip_script "$NCZIP_SCRIPT" \
                           --ncequal_script "$NCEQUAL_SCRIPT" \
                           --varnum "$VARNUM"
