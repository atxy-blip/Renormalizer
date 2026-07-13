# SOP vs TTNO Baseline

This benchmark adds a flat sum-of-products (SOP) operator baseline for TTNS
methodology comparisons.  It represents the ML-MCTDH-style operator layer where

```text
H = sum_r c_r prod_k h_r^(k)
```

is kept as an uncompressed term list and each product term is applied
independently to the same TTNS state.

This is not a Heidelberg ML-MCTDH implementation, not a SPF-equation solver, and
not a new production operator path.  It is an operator-representation baseline:
SOP and TTNO use the same symbolic `Op` terms, the same `BasisTree`, and the same
local basis.

## Why This Is A Fair Comparison

`SOPBaselineOperator` reuses existing `renormalizer.model.Op` terms.  Existing
fermionic parity/Jordan-Wigner strings remain explicit symbolic operators such
as the `Z` strings used in `../ttns-test/junction_zt_hubbard.py`; the baseline does not
guess or rewrite fermion conventions.

For each SOP term the baseline applies cached local operator matrices directly
to the physical axes of the TTNS tensors, then sums the resulting TTNS objects.
It does not construct a one-term TTNO during `apply_to_ttns`, and it does not
compress the full SOP term list into one TTNO before application. Identity sites
are skipped in the term representation.

## Why TTNO Can Win

SOP is a flattened list of product terms.  Its application cost grows directly
with the number of terms and the number of explicit local factors per term.

TTNO represents the operator itself as a tree tensor network.  Shared identity
strings, common subtrees, and repeated bridge/lead/phonon structures can be
encoded once in operator bonds.  TTNO cost is therefore controlled by tree
topology, operator bond dimensions, local dimensions, and TTNS bond dimensions,
not only by raw symbolic term count.

Small systems can favor SOP because TTNO construction and contraction overhead
are visible.  The benchmark is intended to show scaling trends and crossover,
not to claim TTNO is always faster. The current notebook focuses on basis-size
growth in the Hubbard junction model and product-operator count growth in an
artificial shared-structure stress test; TFD is not treated as a separate TTNO
construction benchmark because it is a Hamiltonian preparation choice.

## Running

The molecular-junction benchmark cases are small parameterized variants of
`../ttns-test/junction_zt_hubbard.py`, the Hubbard junction script used for the paper calculations. The benchmark does not import that script directly because it performs argument parsing, logging setup, TTNO construction, TTNS expansion, and time evolution at module import time; instead it reuses the same symbolic operator/tree construction pattern at reduced sizes.

```bash
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case lead --lead-list 1 2 4 8 16 32 --phonon 2 --repeats 7 --output benchmarks/results/lead_scaling.csv
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case phonon --lead 4 --phonon-list 1 2 4 8 16 32 --repeats 7 --output benchmarks/results/phonon_scaling.csv
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case shared-structure --size-list 4 8 16 32 64 --rank-list 1 2 4 --repeats 7 --output benchmarks/results/shared_structure_scaling.csv
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/create_sop_vs_ttno_notebook.py
```

Default arguments are intentionally smaller than the full scaling commands.
Results are written to CSV files in `benchmarks/results/`.  The notebook summary
is generated at `benchmarks/results/sop_vs_ttno_summary.ipynb`; PNG figures are
written to the same directory.

The checked-in small CSV files use reduced ranges and repeat counts so they can
be regenerated quickly on a single workstation.  The commands above are the
recommended longer scaling runs.


## Slurm Array Scaling Run

For denser scaling data on Curie, use the Slurm array script:

```bash
sbatch benchmarks/archive/legacy_sop_vs_ttno/curie_sop_vs_ttno_array.sh
```

The script launches one benchmark point per array task and writes per-point CSV
files under `benchmarks/results/slurm_points/`.  The default grid is:

- lead basis scaling: `n_lead = 1 2 4 8 12 16 24 32`, fixed `n_phonon = 2`;
- phonon basis scaling: `n_phonon = 1 2 4 8 12 16 24 32`, fixed `n_lead = 4`;
- operator-count stress test: `size = 4 6 8 10 12 14 16` and `rank = 1 2 4`.

The defaults request one node, four CPU threads, 128 GB memory, and an 8 hour
wall time.  The stress-test grid intentionally stops at `size=16` because this
case is designed to make flat SOP traversal expensive; larger `size=32/64`
points should be run only after inspecting the `size=16` timings.

Useful overrides are environment variables passed to `sbatch`:

```bash
sbatch --export=ALL,REPEATS=5,TIMEOUT_PER_POINT=3h benchmarks/archive/legacy_sop_vs_ttno/curie_sop_vs_ttno_array.sh
```

After the array finishes, merge per-point CSV files and rebuild the notebook:

```bash
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/merge_sop_vs_ttno_results.py
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/create_sop_vs_ttno_notebook.py
```

## Output Fields

The CSV includes term counts, nontrivial local-operator counts, TTNO bond and
tensor sizes, build/apply/expectation timings, relative apply error,
expectation error, and `tracemalloc` peak memory estimates for SOP and TTNO.
Construction, apply, and expectation timings are separated.  Apply and
expectation timings use warm-up calls followed by repeat medians.
