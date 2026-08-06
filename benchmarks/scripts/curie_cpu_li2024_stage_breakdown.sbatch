#!/bin/bash
#SBATCH --time=00:30:00
#SBATCH --job-name=li2024_stage_breakdown
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=8GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/operator_env_scaling/li2024_construction/logs/stage_breakdown_%j.log

set -eo pipefail

source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9
set -u

export RENO_NUM_THREADS=1
export RENO_GPU=cpu
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-stage-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
RAW=${RAW:-benchmarks/results/operator_env_scaling/li2024_formal/li2024_formal_raw.csv}
OUTPUT_PREFIX=${OUTPUT_PREFIX:-benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713}

cd "$REPO_DIR"

python -u -m benchmarks.analyze_li2024_stage_breakdown \
    --raw "$RAW" \
    --output-prefix "$OUTPUT_PREFIX"
