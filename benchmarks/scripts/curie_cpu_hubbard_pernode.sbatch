#!/bin/bash
#SBATCH --time=02:00:00
#SBATCH --job-name=hubbard_pernode
#SBATCH --array=0-1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=32GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/operator_env_scaling/hubbard_pernode/logs/task_%A_%a.log

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

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
RESULT_ROOT=${RESULT_ROOT:-benchmarks/results/operator_env_scaling/hubbard_pernode}
SNAPSHOT_DIR=${SNAPSHOT_DIR:-${RESULT_ROOT}/snapshots}

cd "$REPO_DIR"
mkdir -p "$RESULT_ROOT/logs" "$SNAPSHOT_DIR"

python -u -m benchmarks.run_hubbard_pernode_point \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --snapshot-dir "$SNAPSHOT_DIR" \
    --timeout-sec 7000 \
    --memory-limit-mb 30000
