#!/bin/bash
#SBATCH --time=0-02:00:00
#SBATCH --job-name=sop_cpu_validation
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=64GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/slurm_logs/sop_cpu_validation_%j.log

set -euo pipefail

# CPU-only validation for SOP/TTNO correctness checks.
# This follows /software/sbatch_examples/python_example.sbatch for environment setup
# and intentionally avoids GPU modules or multi-threaded BLAS settings.

source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9

export RENO_NUM_THREADS=1
export RENO_GPU=cpu
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
cd "$REPO_DIR"

mkdir -p benchmarks/results/slurm_logs

echo "=================================================="
echo "Job: ${SLURM_JOB_ID:-local}"
echo "Host: $(hostname)"
echo "Repo: $REPO_DIR"
echo "Python: $(which python)"
python --version
echo "RENO_NUM_THREADS=$RENO_NUM_THREADS"
echo "RENO_GPU=$RENO_GPU"
echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"
echo "MKL_NUM_THREADS=$MKL_NUM_THREADS"
echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
echo "Started: $(date)"
echo "=================================================="

python -m py_compile \
    renormalizer/tn/sop_baseline.py \
    renormalizer/tn/tests/test_sop_baseline_dense.py

python -m pytest \
    renormalizer/tn/tests/test_sop_baseline.py \
    renormalizer/tn/tests/test_sop_baseline_dense.py \
    renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py \
    -q

echo "Finished: $(date)"
exit 0
