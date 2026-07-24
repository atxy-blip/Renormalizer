# Contraction Scaling Figures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate two validated diagnostic figures and a reproducible fit table from the completed contraction-scaling aggregate.

**Architecture:** A focused plotting module owns CSV loading, log--log fitting, and the two figure builders.  It consumes the existing repeat summary without changing benchmark or aggregation behavior.  Tests exercise its public data and rendering interfaces with synthetic rows before it is run on the full dataset.

**Tech Stack:** Python 3.9, standard-library CSV, NumPy, Matplotlib, pytest.

## Global Constraints

- Use `conda run -n reno-3.9 python ...` for project commands.
- Treat all existing NPZ and aggregate CSV files as immutable inputs.
- Fit medians, use the largest four parameter values for displayed tail exponents, and retain all-point fits in `plot_fits.csv`.
- Write both PDF and 300-DPI PNG figures.

---

### Task 1: Fit and rendering contract

**Files:**
- Create: `renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py`
- Create: `benchmarks/plot_contraction_scaling_diagnostics.py`

**Interfaces:**
- Consumes: summary CSV rows produced by `summarize_repeats()`.
- Produces: `read_summary(path)`, `log_fit(rows, x_field, y_field, tail=None)`, and `generate_figures(summary_path, output_dir)`.

- [x] **Step 1: Write failing tests**

Test that numeric dimensions are sorted numerically, a synthetic `y=3*x^4`
law returns exponent 4, the last four points are selected for a tail fit, and
`generate_figures()` declares all five output paths.

- [x] **Step 2: Run the focused test and verify RED**

Run:
`conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py -q`

Expected: import failure because the plotting module does not yet exist.

- [x] **Step 3: Implement the minimal plotting module**

Implement strict numeric parsing, positive-value log fitting, reusable median
and error-band plotting, both 2-by-2 figures, and deterministic CSV writing.

- [x] **Step 4: Run the focused test and verify GREEN**

Run the same pytest command. Expected: all focused tests pass.

### Task 2: Full-data generation and interpretation

**Files:**
- Create: `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf`
- Create: `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png`
- Create: `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf`
- Create: `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png`
- Create: `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/plot_fits.csv`

**Interfaces:**
- Consumes: the complete 48-row repeat summary.
- Produces: publication-ready visual diagnostics and their exact displayed fits.

- [x] **Step 1: Run the plotter on the completed aggregate**

Set `MPLCONFIGDIR=/tmp/matplotlib-contraction-scaling` and run the module with
the formal summary and figures directory.

- [x] **Step 2: Inspect numerical outputs**

Confirm `plot_fits.csv` contains internal FLOP, leaf FLOP, microkernel timing,
full-model stage timing, tensor-element, and memory fits for both all-point and
largest-four windows.

- [x] **Step 3: Inspect both PNG files visually**

Check labels, log scales, legends, clipping, overlap, and consistency with the
fit table.

- [x] **Step 4: Run regression verification**

Run focused tests, the existing contraction diagnostic tests, `py_compile`,
and `git diff --check`; report the actual outputs and any remaining caveats.
