#!/bin/bash
#SBATCH --time=0-08:00:00
#SBATCH --job-name="sop_ttno"
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --partition=4A100,4V100
#SBATCH --output=benchmarks/results/slurm_logs/sop_ttno_%A_%a.log
#SBATCH --mem=128GB
#SBATCH --qos=normal
#SBATCH --array=0-36

set -uo pipefail

# Slurm array benchmark for SOP vs TTNO operator representation scaling.
# Each task runs one benchmark point and writes one CSV into
# benchmarks/results/slurm_points/.  Merge them afterwards with:
#   conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/merge_sop_vs_ttno_results.py
#   conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/create_sop_vs_ttno_notebook.py

module load cuda/12.4 || true
source /software/devtools/anaconda3/etc/profile.d/conda.sh
conda activate reno-3.9

export RENO_NUM_THREADS=${RENO_NUM_THREADS:-4}
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-4}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-4}
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib-${USER}}

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
cd "$REPO_DIR"

mkdir -p benchmarks/results/slurm_points benchmarks/results/slurm_logs

REPEATS=${REPEATS:-7}
PHONON_FIXED=${PHONON_FIXED:-2}
LEAD_FIXED=${LEAD_FIXED:-4}
TIMEOUT_PER_POINT=${TIMEOUT_PER_POINT:-6h}
TASK_ID=${SLURM_ARRAY_TASK_ID:-0}

# Basis-size scaling for the Hubbard junction builder.  n_lead corresponds to
# junction_zt_hubbard.py --nemode; total lead spin/electrode sites scale as 4*n_lead.
LEAD_POINTS=(1 2 4 8 12 16 24 32)
PHONON_POINTS=(1 2 4 8 12 16 24 32)

# Operator-count stress test.  This deliberately stresses flattened SOP term
# traversal; size=16 was already slow interactively, so the default grid stops
# there. Increase these arrays only after checking the previous run.
SHARED_SIZES=(4 6 8 10 12 14 16)
SHARED_RANKS=(1 2 4)

N_LEAD=${#LEAD_POINTS[@]}
N_PHONON=${#PHONON_POINTS[@]}
N_SHARED=$(( ${#SHARED_SIZES[@]} * ${#SHARED_RANKS[@]} ))
N_TOTAL=$(( N_LEAD + N_PHONON + N_SHARED ))

if (( TASK_ID < 0 || TASK_ID >= N_TOTAL )); then
    echo "Invalid SLURM_ARRAY_TASK_ID=$TASK_ID for N_TOTAL=$N_TOTAL" >&2
    exit 2
fi

if (( TASK_ID < N_LEAD )); then
    CASE="lead"
    NLEAD=${LEAD_POINTS[$TASK_ID]}
    OUT="benchmarks/results/slurm_points/lead_nlead${NLEAD}_phonon${PHONON_FIXED}.csv"
    CMD=(python -u benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case lead --lead-list "$NLEAD" --phonon "$PHONON_FIXED" --repeats "$REPEATS" --output "$OUT")
elif (( TASK_ID < N_LEAD + N_PHONON )); then
    IDX=$(( TASK_ID - N_LEAD ))
    CASE="phonon"
    NPH=${PHONON_POINTS[$IDX]}
    OUT="benchmarks/results/slurm_points/phonon_lead${LEAD_FIXED}_nphonon${NPH}.csv"
    CMD=(python -u benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case phonon --lead "$LEAD_FIXED" --phonon-list "$NPH" --repeats "$REPEATS" --output "$OUT")
else
    IDX=$(( TASK_ID - N_LEAD - N_PHONON ))
    RANK_IDX=$(( IDX / ${#SHARED_SIZES[@]} ))
    SIZE_IDX=$(( IDX % ${#SHARED_SIZES[@]} ))
    CASE="shared-structure"
    RANK=${SHARED_RANKS[$RANK_IDX]}
    SIZE=${SHARED_SIZES[$SIZE_IDX]}
    OUT="benchmarks/results/slurm_points/shared_size${SIZE}_rank${RANK}.csv"
    CMD=(python -u benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case shared-structure --size-list "$SIZE" --rank-list "$RANK" --repeats "$REPEATS" --output "$OUT")
fi

echo "=================================================="
echo "Job: ${SLURM_JOB_ID:-local} task ${TASK_ID}/${N_TOTAL}"
echo "Case: $CASE"
echo "Repeats: $REPEATS"
echo "Output: $OUT"
echo "Timeout per point: $TIMEOUT_PER_POINT"
echo "Command: ${CMD[*]}"
echo "Started: $(date)"
echo "=================================================="

/usr/bin/time -f 'elapsed=%e maxrss_kb=%M' timeout "$TIMEOUT_PER_POINT" "${CMD[@]}"

STATUS=$?
echo "Finished: $(date) status=$STATUS"
exit $STATUS
