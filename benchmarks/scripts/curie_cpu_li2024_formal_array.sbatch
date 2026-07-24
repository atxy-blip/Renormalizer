#!/bin/bash
#SBATCH --time=3-00:00:00
#SBATCH --job-name=li2024_op_scale
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=128GB
#SBATCH --qos=normal
#SBATCH --array=0-188%12
#SBATCH --output=benchmarks/results/operator_env_scaling/li2024_formal/logs/task_%A_%a.log

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
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
MANIFEST=${MANIFEST:-benchmarks/results/operator_env_scaling/li2024_formal/manifest.tsv}
SNAPSHOT_DIR=${SNAPSHOT_DIR:-benchmarks/results/operator_env_scaling/li2024_formal/snapshots}
TIMEOUT_SEC=${TIMEOUT_SEC:-250000}
MEMORY_LIMIT_MB=${MEMORY_LIMIT_MB:-120000}

cd "$REPO_DIR"

python -u -m benchmarks.run_li2024_formal_point \
    --manifest "$MANIFEST" \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --snapshot-dir "$SNAPSHOT_DIR" \
    --timeout-sec "$TIMEOUT_SEC" \
    --memory-limit-mb "$MEMORY_LIMIT_MB"
