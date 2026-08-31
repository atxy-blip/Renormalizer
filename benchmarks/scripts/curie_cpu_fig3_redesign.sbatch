#!/bin/bash
#SBATCH --time=1-00:00:00
#SBATCH --job-name=fig3_redesign
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=128GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/operator_env_scaling/runs/fig3_%j_%x.log

set -euo pipefail

# Fig 3 redesign wrapper: one job runs one (tree_topology, orbital_layout,
# jw_ordering, U) balanced lead-phonon scan.
#
# Env controls:
#   REPO_DIR                cluster checkout (default /curie-home/yuxiong/Reno-quantity)
#   RUN_TAG                 label appended to output names (default fig3)
#   TREE_TOPOLOGY           bridge_centered | flattened_binary | lead_split
#   ORBITAL_LAYOUT          energy | spin_blocked   (which mode sits on which leaf)
#   JW_ORDERING             tree_order | energy_order (where the JW strings run)
#   HUBBARD_U, HUBBARD_ED   bridge energies in eV
#   BALANCED_PAIRS          "n_lead:n_phonon" pairs (default 4:1 8:2 16:4 32:8 64:16)
#   BALANCED_STATE_BOND     M_s for all balanced points (default 20)
#   BALANCED_PRIMITIVE_BASIS d for all balanced points (default 10)
#   METHODS                 semicolon list (commas break `sbatch --export`);
#                           default sop_no_env;sop_mctdh_like_state_env;ttno_with_env
#   REPEATS, TIMEOUT_SEC, MEMORY_LIMIT_MB, MAX_EXTRA_POINTS

# The site profile and conda's activate.d hooks reference unset variables
# (e.g. QT_XCB_GL_INTEGRATION), which `set -u` turns into a fatal error.
set +u
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
RUN_TAG=${RUN_TAG:-fig3}
TREE_TOPOLOGY=${TREE_TOPOLOGY:-bridge_centered}
ORBITAL_LAYOUT=${ORBITAL_LAYOUT:-energy}
JW_ORDERING=${JW_ORDERING:-tree_order}
HUBBARD_U=${HUBBARD_U:-0.0}
HUBBARD_ED=${HUBBARD_ED:-0.0}
# Semicolon-separated in env exports (no spaces); normalized to spaces below.
BALANCED_PAIRS=${BALANCED_PAIRS:-"4:1;8:2;16:4;32:8;64:16"}
BALANCED_PAIRS=$(echo "$BALANCED_PAIRS" | tr ';' ' ')
BALANCED_STATE_BOND=${BALANCED_STATE_BOND:-20}
BALANCED_PRIMITIVE_BASIS=${BALANCED_PRIMITIVE_BASIS:-10}
METHODS=${METHODS:-"sop_no_env;sop_mctdh_like_state_env;ttno_with_env"}
# Semicolon-separated too: a comma here would be eaten by `sbatch --export`.
METHODS=$(echo "$METHODS" | tr ';' ',')
ACTIVE_SCOPE=${ACTIVE_SCOPE:-all_nodes}
REPEATS=${REPEATS:-3}
TIMEOUT_SEC=${TIMEOUT_SEC:-3600}
MEMORY_LIMIT_MB=${MEMORY_LIMIT_MB:-110000}
MAX_EXTRA_POINTS=${MAX_EXTRA_POINTS:-0}

cd "$REPO_DIR"
mkdir -p benchmarks/results/operator_env_scaling/runs

OUT_PREFIX="benchmarks/results/operator_env_scaling/runs/fig3_${RUN_TAG}_${SLURM_JOB_ID:-local}"
RAW_OUT="${OUT_PREFIX}_raw.csv"
FIT_OUT="${OUT_PREFIX}_fits.csv"

echo "=================================================="
echo "Job: ${SLURM_JOB_ID:-local}  Tag: $RUN_TAG"
echo "Host: $(hostname)  Repo: $REPO_DIR"
python --version
echo "TREE_TOPOLOGY=$TREE_TOPOLOGY"
echo "ORBITAL_LAYOUT=$ORBITAL_LAYOUT JW_ORDERING=$JW_ORDERING"
echo "HUBBARD_U=$HUBBARD_U HUBBARD_ED=$HUBBARD_ED"
echo "BALANCED_PAIRS=$BALANCED_PAIRS"
echo "BALANCED_STATE_BOND=$BALANCED_STATE_BOND BALANCED_PRIMITIVE_BASIS=$BALANCED_PRIMITIVE_BASIS"
echo "METHODS=$METHODS ACTIVE_SCOPE=$ACTIVE_SCOPE"
echo "REPEATS=$REPEATS TIMEOUT_SEC=$TIMEOUT_SEC MEMORY_LIMIT_MB=$MEMORY_LIMIT_MB"
echo "Started: $(date)"
echo "=================================================="

python -u benchmarks/benchmark_adaptive_operator_env.py \
    --scaling-path balanced_lead_phonon \
    --balanced-pairs "$BALANCED_PAIRS" \
    --balanced-state-bond "$BALANCED_STATE_BOND" \
    --balanced-primitive-basis "$BALANCED_PRIMITIVE_BASIS" \
    --hubbard-u "$HUBBARD_U" \
    --hubbard-ed "$HUBBARD_ED" \
    --tree-topology "$TREE_TOPOLOGY" \
    --orbital-layout "$ORBITAL_LAYOUT" \
    --jw-ordering "$JW_ORDERING" \
    --methods "$METHODS" \
    --active-scope "$ACTIVE_SCOPE" \
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
