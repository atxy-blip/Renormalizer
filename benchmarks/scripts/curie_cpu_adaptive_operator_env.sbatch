#!/bin/bash
#SBATCH --time=0-12:00:00
#SBATCH --job-name=adaptive_operator_env
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=128GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/slurm_logs/adaptive_operator_env_%j.log

set -euo pipefail

# CPU-only adaptive benchmark wrapper.
# RUN_PROFILE controls size:
#   sanity: correctness/smoke only, not for scaling conclusions
#   medium: server-scale trend check
#   large:  server-scale log-log fitting run

source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9

export RENO_NUM_THREADS=1
export RENO_GPU=cpu
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
RUN_PROFILE=${RUN_PROFILE:-sanity}
cd "$REPO_DIR"

mkdir -p benchmarks/results/slurm_logs benchmarks/results/adaptive_operator_env

case "$RUN_PROFILE" in
    sanity)
        LEAD_VALUES=${LEAD_VALUES:-"4 8"}
        BALANCED_PAIRS=${BALANCED_PAIRS:-"4:1 8:2"}
        REPEATS=${REPEATS:-1}
        TIMEOUT_SEC=${TIMEOUT_SEC:-600}
        MEMORY_LIMIT_MB=${MEMORY_LIMIT_MB:-0}
        MAX_EXTRA_POINTS=${MAX_EXTRA_POINTS:-0}
        ;;
    medium)
        LEAD_VALUES=${LEAD_VALUES:-"4 8 16 32"}
        BALANCED_PAIRS=${BALANCED_PAIRS:-"4:1 8:2 16:4 32:8"}
        REPEATS=${REPEATS:-3}
        TIMEOUT_SEC=${TIMEOUT_SEC:-1800}
        MEMORY_LIMIT_MB=${MEMORY_LIMIT_MB:-110000}
        MAX_EXTRA_POINTS=${MAX_EXTRA_POINTS:-0}
        ;;
    large)
        LEAD_VALUES=${LEAD_VALUES:-"4 8 16 32 64 128"}
        BALANCED_PAIRS=${BALANCED_PAIRS:-"4:1 8:2 16:4 32:8 64:16"}
        REPEATS=${REPEATS:-3}
        TIMEOUT_SEC=${TIMEOUT_SEC:-3600}
        MEMORY_LIMIT_MB=${MEMORY_LIMIT_MB:-110000}
        MAX_EXTRA_POINTS=${MAX_EXTRA_POINTS:-1}
        ;;
    *)
        echo "Unknown RUN_PROFILE=$RUN_PROFILE; expected sanity, medium, or large" >&2
        exit 2
        ;;
esac

OUT_PREFIX="benchmarks/results/adaptive_operator_env/${RUN_PROFILE}_${SLURM_JOB_ID:-local}"
RAW_OUT="${OUT_PREFIX}_raw.csv"
FIT_OUT="${OUT_PREFIX}_fits.csv"

echo "=================================================="
echo "Job: ${SLURM_JOB_ID:-local}"
echo "Profile: $RUN_PROFILE"
echo "Host: $(hostname)"
echo "Repo: $REPO_DIR"
echo "Python: $(which python)"
python --version
echo "LEAD_VALUES=$LEAD_VALUES"
echo "BALANCED_PAIRS=$BALANCED_PAIRS"
echo "REPEATS=$REPEATS"
echo "TIMEOUT_SEC=$TIMEOUT_SEC"
echo "MEMORY_LIMIT_MB=$MEMORY_LIMIT_MB"
echo "MAX_EXTRA_POINTS=$MAX_EXTRA_POINTS"
echo "RENO_NUM_THREADS=$RENO_NUM_THREADS"
echo "RENO_GPU=$RENO_GPU"
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "Started: $(date)"
echo "=================================================="

python -u benchmarks/benchmark_adaptive_operator_env.py \
    --scaling-path all \
    --lead-values "$LEAD_VALUES" \
    --balanced-pairs "$BALANCED_PAIRS" \
    --repeats "$REPEATS" \
    --timeout-sec "$TIMEOUT_SEC" \
    --memory-limit-mb "$MEMORY_LIMIT_MB" \
    --max-extra-points "$MAX_EXTRA_POINTS" \
    --output "$RAW_OUT" \
    --fit-output "$FIT_OUT"

echo "Finished: $(date)"
echo "Raw CSV: $RAW_OUT"
echo "Fit CSV: $FIT_OUT"
exit 0
