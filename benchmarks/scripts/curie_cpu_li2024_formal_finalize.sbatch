#!/bin/bash
#SBATCH --time=00:30:00
#SBATCH --job-name=li2024_op_plot
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=4GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/operator_env_scaling/li2024_formal/logs/finalize_%j.log

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
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-li2024-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
RESULT_ROOT=${RESULT_ROOT:-benchmarks/results/operator_env_scaling/li2024_formal}
FINAL_ROOT=${FINAL_ROOT:-benchmarks/results/operator_env_scaling/final}
FIGURES_DIR=${FIGURES_DIR:-benchmarks/results/operator_env_scaling/figures}
MANIFEST=${MANIFEST:-${RESULT_ROOT}/manifest.tsv}
SNAPSHOT_DIR=${SNAPSHOT_DIR:-${RESULT_ROOT}/snapshots}
RAW_OUTPUT=${RAW_OUTPUT:-${RESULT_ROOT}/li2024_formal_raw.csv}
MISSING_OUTPUT=${MISSING_OUTPUT:-${RESULT_ROOT}/missing_or_error_tasks.json}
OUTPUT_PREFIX=${OUTPUT_PREFIX:-${FINAL_ROOT}/li2024_spin_boson_20260713}

cd "$REPO_DIR"
mkdir -p "$FIGURES_DIR"

python -u -m benchmarks.finalize_li2024_formal \
    --manifest "$MANIFEST" \
    --snapshot-dir "$SNAPSHOT_DIR" \
    --raw-output "$RAW_OUTPUT" \
    --missing-output "$MISSING_OUTPUT" \
    --output-prefix "$OUTPUT_PREFIX" \
    --figures-dir "$FIGURES_DIR"
