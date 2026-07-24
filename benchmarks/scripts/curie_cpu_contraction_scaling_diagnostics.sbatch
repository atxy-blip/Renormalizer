#!/bin/bash
#SBATCH --time=1-00:00:00
#SBATCH --job-name=tn_contract_diag
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=64GB
#SBATCH --qos=normal
#SBATCH --array=0-143%8
#SBATCH --output=benchmarks/results/operator_env_scaling/contraction_diagnostics/logs/task_%A_%a.log

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
MANIFEST=${MANIFEST:-benchmarks/results/operator_env_scaling/contraction_diagnostics/manifest.tsv}
SNAPSHOT_DIR=${SNAPSHOT_DIR:-benchmarks/results/operator_env_scaling/contraction_diagnostics/snapshots}

cd "$REPO_DIR"

python -u -m benchmarks.run_contraction_scaling_diagnostic \
    --manifest "$MANIFEST" \
    --task-id "$SLURM_ARRAY_TASK_ID" \
    --snapshot-dir "$SNAPSHOT_DIR"
