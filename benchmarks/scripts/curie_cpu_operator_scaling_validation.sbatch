#!/bin/bash
#SBATCH --time=0-02:00:00
#SBATCH --job-name=op_scaling_validation
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=64GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/slurm_logs/op_scaling_validation_%j.log

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
cd "$REPO_DIR"

mkdir -p benchmarks/results/slurm_logs

echo "Job: ${SLURM_JOB_ID:-local} Host: $(hostname)"

python -m py_compile \
    benchmarks/plot_li2024_operator_scaling.py \
    benchmarks/finalize_li2024_formal.py \
    renormalizer/tn/sop_baseline.py

python -m pytest \
    renormalizer/tn/tests/test_sop_baseline.py \
    renormalizer/tn/tests/test_sop_baseline_dense.py \
    renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py \
    renormalizer/tn/tests/test_li2024_formal_benchmark.py \
    renormalizer/tn/tests/test_contraction_scaling_diagnostics.py \
    renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py \
    renormalizer/tn/tests/test_nature_plot_style.py \
    -q

echo "Finished: $(date)"
exit 0
