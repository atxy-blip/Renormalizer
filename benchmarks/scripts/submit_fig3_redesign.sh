#!/bin/bash
# Submit the Fig 3 redesign benchmark jobs on Curie.
#
# Usage:
#   cd /curie-home/yuxiong/Reno-quantity
#   bash benchmarks/scripts/submit_fig3_redesign.sh            # everything
#   bash benchmarks/scripts/submit_fig3_redesign.sh panel_c    # panel (c) only
#
# Queues, in order:
#   1-2. sanity smoke tests (baseline + panel-c layout, small pairs, 1 repeat)
#   3-4. panel (a) and (b): bridge-centered tree, energy layout, U_d = 0 and 1 eV
#   5-6. panel (c): same tree, spin-blocked layout, JW rebuilt in tree order vs
#        kept in stale energy order.  Both are the same Hamiltonian; only the
#        TTNO feels the difference, so these two runs carry the whole panel.
#   7.   optional SI control: bad flattened-binary tree at U_d = 0
#
# Panel (c) deliberately drops sop_no_env: panels (a)/(b) already establish its
# N^3 exponent, and at N >= 138 it costs ~1.7 h per repeat, which would triple
# the panel's cost to show a curve that is insensitive to the varied knob.
#
# The sop_no_env method exceeds the per-point time budget at the largest points
# in jobs 3-4 and is automatically disabled by the benchmark afterwards, exactly
# as in the published 42/45 run. BALANCED_PAIRS uses ';' separators because the
# values travel through Slurm --export (the wrapper converts them to spaces).

set -euo pipefail

WRAPPER=benchmarks/scripts/curie_cpu_fig3_redesign.sbatch
PAIRS="4:1;8:2;16:4;32:8;64:16"
# Panel (c) needs one point beyond the panel (a)/(b) range: the stale-JW cost
# only reaches its asymptotic N^2 above N ~ 300 (local slope 1.66 at N=138,
# 1.97 at N=274, 2.04 at N=546), so a fit stopping at N=274 still averages over
# the crossover and reads ~1.6.  sop_no_env is excluded here, which is what
# makes the extra point affordable.
PAIRS_C="4:1;8:2;16:4;32:8;64:16;128:32"
WHICH=${1:-all}

run_job() {
    # run_job <tag> [KEY=VALUE ...]   (KEY=VALUE pairs become extra env exports;
    # later duplicates override earlier ones)
    local tag=$1
    shift
    declare -A envs
    envs[RUN_TAG]="$tag"
    envs[BALANCED_PAIRS]="$PAIRS"
    for pair in "$@"; do
        envs[${pair%%=*}]="${pair#*=}"
    done
    local extra=""
    for key in "${!envs[@]}"; do
        extra="${extra},${key}=${envs[$key]}"
    done
    sbatch --parsable --export="ALL${extra}" "$WRAPPER"
}

if [[ "$WHICH" == "all" || "$WHICH" == "sanity" ]]; then
    # 1-2. Sanity smoke tests first: catch tree-builder or QN problems cheaply.
    echo "Submitting sanity jobs..."
    run_job sanity_baseline REPEATS=1 TIMEOUT_SEC=600 BALANCED_PAIRS="4:1;8:2"
    run_job sanity_jwstale REPEATS=1 TIMEOUT_SEC=600 BALANCED_PAIRS="4:1;8:2" \
        ORBITAL_LAYOUT=spin_blocked JW_ORDERING=energy_order
fi

if [[ "$WHICH" == "all" || "$WHICH" == "panel_ab" ]]; then
    # 3-4. Panels (a) and (b): Hubbard term off and on.
    for U in 0.0 1.0; do
        echo "Submitting panel-ab U=${U}..."
        run_job "good_u${U}" HUBBARD_U="${U}"
    done
fi

if [[ "$WHICH" == "all" || "$WHICH" == "panel_c" ]]; then
    # 5-6. Panel (c): one tree, one layout, two Jordan-Wigner orderings.
    echo "Submitting panel-c JW-aligned..."
    run_job jw_tree_order BALANCED_PAIRS="$PAIRS_C" TIMEOUT_SEC=7200 \
        ORBITAL_LAYOUT=spin_blocked JW_ORDERING=tree_order \
        METHODS="sop_mctdh_like_state_env;ttno_with_env"
    echo "Submitting panel-c JW-stale..."
    run_job jw_energy_order BALANCED_PAIRS="$PAIRS_C" TIMEOUT_SEC=7200 \
        ORBITAL_LAYOUT=spin_blocked JW_ORDERING=energy_order \
        METHODS="sop_mctdh_like_state_env;ttno_with_env"
fi

if [[ "$WHICH" == "si" ]]; then
    # 7. SI control: bad tree at U=0 (topology change alone leaves the exponents
    # untouched, which is why panel (c) varies the JW ordering instead).
    echo "Submitting bad-tree U=0..."
    run_job bad_u0 TREE_TOPOLOGY=flattened_binary HUBBARD_U=0.0
fi

echo "All jobs submitted. Track with: squeue -u \$USER"
echo "After completion, copy *_raw.csv into one directory and run:"
echo "  python benchmarks/check_fig3_data.py --csv-dir <dir>"
echo "  python benchmarks/plot_paper_figures_3panel.py --csv-dir <dir> --output Fig3_operator_scaling.pdf --png"
