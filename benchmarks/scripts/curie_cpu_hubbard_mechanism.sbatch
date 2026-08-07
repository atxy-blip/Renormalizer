#!/bin/bash
#SBATCH --time=00:30:00
#SBATCH --job-name=hubbard_mechanism
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=8GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/operator_env_scaling/hubbard_balanced/logs/mechanism_%j.log

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
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-mechanism-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
FINAL_ROOT=${FINAL_ROOT:-benchmarks/results/operator_env_scaling/final}
FIGURES_DIR=${FIGURES_DIR:-benchmarks/results/operator_env_scaling/figures}
OUTPUT_PREFIX=${OUTPUT_PREFIX:-${FINAL_ROOT}/hubbard_junction_20260806}

cd "$REPO_DIR"
mkdir -p "$FIGURES_DIR"

python -u -m benchmarks.analyze_hubbard_mechanism \
    --output-prefix "$OUTPUT_PREFIX" \
    --figures-dir "$FIGURES_DIR"
