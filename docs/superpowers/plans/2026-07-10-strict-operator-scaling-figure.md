# Strict Operator Scaling Figure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate one strict all-node scaling PDF with only the three theoretical baselines and reorganize all previous benchmark artifacts into clearly labeled archives.

**Architecture:** Keep the adaptive benchmark as the active data producer and narrow the plotting script to a publication-facing consumer. Preserve the completed job 114336 raw CSV as the final source of truth, regenerate summary/fits beside the PDF, and move every older artifact into an archive classified by timing object and algorithm identity.

**Tech Stack:** Python 3.9, csv, NumPy, Matplotlib, pytest, Slurm result files, Markdown manifests.

## Global Constraints

- The final figure contains only `sop_no_env`, `sop_mctdh_like_state_env`, and `ttno_with_env`.
- The horizontal axis is `N_total_sites`; both axes are logarithmic.
- Dashed reference lines have theoretical slopes `alpha=3`, `alpha=2`, and `alpha=1`.
- Generate PDF only; do not generate PNG.
- Preserve historical raw data, figures, fits, logs, and scripts by moving them into named archives rather than deleting them.
- Do not query or submit Slurm jobs.

---

### Task 1: Publication Plot Contract

**Files:**
- Create: `renormalizer/tn/tests/test_operator_env_scaling_plot.py`
- Modify: `benchmarks/plot_operator_env_scaling.py`

**Interfaces:**
- Consumes: raw benchmark rows with `quantity=local_effective_1site_apply_all_nodes`.
- Produces: `PUBLICATION_METHODS`, `REFERENCE_ALPHA`, `reference_curve(x, y, alpha)`, and a PDF-only CLI.

- [ ] **Step 1: Write failing tests for method filtering and reference slopes**

```python
import numpy as np

from benchmarks.plot_operator_env_scaling import (
    PUBLICATION_METHODS,
    REFERENCE_ALPHA,
    reference_curve,
)


def test_publication_methods_exclude_operator_cache():
    assert PUBLICATION_METHODS == (
        "sop_no_env",
        "sop_mctdh_like_state_env",
        "ttno_with_env",
    )
    assert "sop_env_plus_operator_cache" not in PUBLICATION_METHODS


def test_reference_curves_have_requested_log_log_slopes():
    x = np.array([16.0, 32.0, 64.0])
    y = np.array([2.0, 8.0, 32.0])
    for alpha in REFERENCE_ALPHA.values():
        x_ref, y_ref = reference_curve(x, y, alpha)
        measured = np.diff(np.log(y_ref)) / np.diff(np.log(x_ref))
        np.testing.assert_allclose(measured, alpha)
```

- [ ] **Step 2: Run the focused tests and confirm they fail before implementation**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_operator_env_scaling_plot.py -q
```

Expected: import failure for the new publication constants/functions.

- [ ] **Step 3: Narrow the plotter to the publication contract**

Implement these constants and helper:

```python
PUBLICATION_METHODS = (
    "sop_no_env",
    "sop_mctdh_like_state_env",
    "ttno_with_env",
)
REFERENCE_ALPHA = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}


def reference_curve(x, y, alpha):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_anchor = float(np.exp(np.mean(np.log(x))))
    y_anchor = float(np.exp(np.mean(np.log(y))))
    return x, y_anchor * (x / x_anchor) ** alpha
```

Filter publication summary/fits to `PUBLICATION_METHODS`, reject inputs whose
quantity is not all-node, render colored scatter points, and render one dashed
reference line per method. Change the CLI to write:

```text
<output-prefix>_summary.csv
<output-prefix>_fits.csv
<output-prefix>_scaling_vs_nsite.pdf
```

Do not call `savefig()` for PNG or diagnostics.

- [ ] **Step 4: Run focused tests and compilation**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_operator_env_scaling_plot.py -q
conda run -n reno-3.9 python -m py_compile benchmarks/plot_operator_env_scaling.py renormalizer/tn/tests/test_operator_env_scaling_plot.py
```

Expected: tests pass and compilation exits zero.

### Task 2: Archive Layout And Dependency Repair

**Files:**
- Move: `benchmarks/benchmark_sop_vs_ttno.py` to `benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`
- Move: `benchmarks/create_sop_vs_ttno_notebook.py` to `benchmarks/archive/legacy_sop_vs_ttno/create_sop_vs_ttno_notebook.py`
- Move: `benchmarks/merge_sop_vs_ttno_results.py` to `benchmarks/archive/legacy_sop_vs_ttno/merge_sop_vs_ttno_results.py`
- Move: `benchmarks/scripts/curie_sop_vs_ttno_array.sh` to `benchmarks/archive/legacy_sop_vs_ttno/curie_sop_vs_ttno_array.sh`
- Modify: `renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py`
- Create: `benchmarks/archive/legacy_sop_vs_ttno/README.md`
- Create: `benchmarks/results/operator_env_scaling/README.md`
- Create: archive manifests under `benchmarks/results/operator_env_scaling/archive/`

**Interfaces:**
- Consumes: the existing active benchmark builder `benchmarks.benchmark_adaptive_operator_env.build_hubbard_junction_case`.
- Produces: a clean active benchmark root and self-describing historical archives.

- [ ] **Step 1: Repair the legacy test dependency before moving its script**

Change:

```python
from benchmarks.benchmark_sop_vs_ttno import build_hubbard_junction_case
```

to:

```python
from benchmarks.benchmark_adaptive_operator_env import build_hubbard_junction_case
```

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py -q
```

Expected: both equivalence tests pass.

- [ ] **Step 2: Move legacy scripts and write their manifest**

Use `git mv` for tracked scripts. The README must state that these scripts
measure the earlier full-state SOP-vs-TTNO experiment and are retained only
for reproducibility.

- [ ] **Step 3: Move adaptive result families by semantic category**

Move root-only jobs `114110`, `114116`, `114119`, `114123`, `114126`, `114311`,
`114312`, and `114313` into `archive/root_one_site_legacy/`. Move strict
development jobs `114333` and `114334`, job 114336's old diagnostic plots and
benchmark-native fit, and validation logs into
`archive/strict_all_nodes_development/`. Move the original Slurm job 114336
log beside the final data for provenance.

- [ ] **Step 4: Move the early SOP-vs-TTNO result family**

Move `fig_*`, `*_scaling.csv`, `slurm_points/`, `sop_ttno_99434_*.log`, the
summary Markdown/notebook, and `slurm_99434_summary.md` into
`archive/legacy_sop_vs_ttno/`.

- [ ] **Step 5: Write archive manifests and inventory the result tree**

Each manifest records timing object, included job IDs, algorithm identity,
and exclusion reason. Run:

```bash
find benchmarks/results/operator_env_scaling -type f -print | sort
```

Expected: every historical artifact is under exactly one semantic category.

### Task 3: Generate And Verify Final Deliverables

**Files:**
- Move: `medium_114336_raw.csv` to `benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_raw.csv`
- Generate: `benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_summary.csv`
- Generate: `benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_fits.csv`
- Generate: `benchmarks/results/operator_env_scaling/final/strict_all_nodes_scaling_vs_nsite.pdf`
- Modify: relevant `llmdoc` decision/guide/index entries.

**Interfaces:**
- Consumes: the completed job 114336 raw CSV.
- Produces: the sole publication-facing PDF and its compact provenance tables.

- [ ] **Step 1: Generate final tables and PDF**

Run:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -p /software/cache/yuxiong/plot \
python benchmarks/plot_operator_env_scaling.py \
  --raw benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336
```

Expected: two CSV files and one PDF; no PNG.

- [ ] **Step 2: Verify numerical contents**

Check that the fit table contains only three methods and that fitted alpha
values against `N_total_sites` remain approximately `3.25`, `2.17`, and
`1.06`. Confirm all input rows have all-node quantity and relative error below
`1e-12`.

- [ ] **Step 3: Inspect the rendered PDF**

Render the first page to a temporary image, inspect it, and confirm that axes,
legend, scatter points, and dashed `alpha=3/2/1` references are legible and do
not overlap.

- [ ] **Step 4: Run the full focused verification set**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py renormalizer/tn/tests/test_operator_env_scaling_plot.py renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py -q
bash -n benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch benchmarks/scripts/curie_cpu_sop_validation.sbatch
git diff --check
```

Expected: all tests pass, shell scripts parse, and no whitespace errors exist.

- [ ] **Step 5: Update llmdoc with the final result contract**

Record that job 114336 is the final strict all-node source, publication plots
exclude operator cache, the final path is PDF-only, and older root-only results
are archived as historical diagnostics.

