# Recoverable Three-Variable Scaling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce scientifically labelled `N_site/M_s/d` benchmark data and a PDF while preserving completed points when a Slurm job times out.

**Architecture:** Keep the existing benchmark kernels and CSV schema. Add atomic checkpoint writes after every repeat, restrict theoretical `N^3/N^2/N` guides to the `N_site` panel, and submit each scaling variable as an independent Slurm job with explicit parameter ranges.

**Tech Stack:** Python 3.9, pytest, NumPy, Matplotlib, Slurm, Renormalizer TTNS/TTNO.

## Global Constraints

- Use `ACTIVE_SCOPE=all_nodes` for all strict scaling results.
- Publication methods are only `sop_no_env`, `sop_mctdh_like_state_env`, and `ttno_with_env`.
- Do not plot `sop_env_plus_operator_cache`.
- Generate PDF only for the publication figure.
- Preserve the existing raw CSV field names.
- Use `conda run -n reno-3.9 python ...` for tests.

---

### Task 1: Make benchmark output recoverable

**Files:**
- Modify: `benchmarks/benchmark_adaptive_operator_env.py` (`run_benchmark`)
- Test: `renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py`

**Interfaces:**
- Consumes: `run_benchmark(args)` and the existing `write_csv(path, rows, fields)` helper.
- Produces: a raw CSV checkpoint after every completed repeat and a fit CSV checkpoint after every completed point.

- [ ] **Step 1: Write a failing checkpoint test**

Patch `_run_point` to return one valid row and raise `KeyboardInterrupt` on the second repeat. Call `run_benchmark(args)` and assert that `args.output` exists and contains the first repeat despite interruption.

- [ ] **Step 2: Verify the test fails**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py::test_run_benchmark_checkpoints_completed_repeats -q
```

Expected: FAIL because the current function writes only after all paths finish.

- [ ] **Step 3: Add atomic checkpoint writing**

Add `write_csv_atomic(path, rows, fields)`, writing to `path.with_suffix(path.suffix + ".tmp")` and replacing the destination. In `run_benchmark`, append each repeat's rows directly to `rows`, mark overhead rows, and checkpoint raw output immediately. Recompute and checkpoint fits after each completed point. Keep the final writes for normal completion.

- [ ] **Step 4: Verify benchmark tests pass**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py -q
```

Expected: all tests pass.

---

### Task 2: Correct theoretical guide semantics

**Files:**
- Modify: `benchmarks/plot_operator_env_scaling.py` (`ScalingPanel`, `plot_publication_time`)
- Test: `renormalizer/tn/tests/test_operator_env_scaling_plot.py`

**Interfaces:**
- Consumes: `SCALING_PANELS` and `REFERENCE_ALPHA`.
- Produces: `ScalingPanel.reference_alpha_by_method`, populated only for the site-number panel.

- [ ] **Step 1: Write a failing panel-reference test**

Assert that the site-number panel maps the three methods to `3.0`, `2.0`, and `1.0`, while the state-bond and primitive-basis panels have no method-specific reference mapping.

- [ ] **Step 2: Verify the test fails**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_operator_env_scaling_plot.py::test_only_site_panel_has_strict_method_reference_slopes -q
```

Expected: FAIL because every panel currently reads the global mapping.

- [ ] **Step 3: Implement panel-specific guides**

Add a reference mapping field to `ScalingPanel`. In `plot_publication_time`, draw and annotate a dashed guide only when the current method is present in that panel's mapping. Keep dashed lines out of the legend.

- [ ] **Step 4: Verify plot tests pass**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_operator_env_scaling_plot.py -q
```

Expected: all tests pass.

---

### Task 3: Submit split, bounded Slurm runs

**Files:**
- Reuse: `benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch`
- Output: `benchmarks/results/operator_env_scaling/runs/`

**Interfaces:**
- Consumes: environment overrides already accepted by the Slurm wrapper.
- Produces: independent raw and fit CSVs for `lead_only`, `state_bond`, and `primitive_basis`.

- [ ] **Step 1: Verify wrapper syntax**

Run:

```bash
bash -n benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

Expected: exit code 0.

- [ ] **Step 2: Submit recoverable site-number shards**

Submit two jobs so the cubic no-env path cannot consume the whole 12-hour allocation:

```bash
RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=lead_only LEAD_VALUES="4 8 16" REPEATS=3 MAX_EXTRA_POINTS=0 sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=lead_only LEAD_VALUES="32" REPEATS=3 MAX_EXTRA_POINTS=0 sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

The `n_lead=64` no-env point is excluded because one repeat already exceeded the practical 12-hour budget implied by job 114439.

- [ ] **Step 3: Submit a stronger state-bond diagnostic**

Use a smaller fixed tree so higher bonds are affordable and scan beyond 16:

```bash
RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=state_bond STATE_BOND_BASE_LEAD=4 STATE_BOND_BASE_PHONON=0 STATE_BOND_VALUES="4 8 16 32 64" REPEATS=3 MAX_EXTRA_POINTS=0 sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

- [ ] **Step 4: Submit a non-product-state primitive-basis diagnostic**

First extend `_scaling_points` so primitive-basis points use a configurable `--primitive-basis-state-bond` rather than hard-coded `1`, then submit with `M_s=16`, more phonons than leads, and `d` crossing `M_s`:

```bash
RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=primitive_basis PRIMITIVE_BASIS_BASE_LEAD=1 PRIMITIVE_BASIS_BASE_PHONON=16 PRIMITIVE_BASIS_VALUES="4 8 16 32" PRIMITIVE_BASIS_STATE_BOND=16 REPEATS=3 MAX_EXTRA_POINTS=0 sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

- [ ] **Step 5: Record job IDs and exact parameters**

Append the submitted IDs and environment overrides to `benchmarks/results/operator_env_scaling/runs/README.md` so later analysis can distinguish shards and diagnostic redesigns.

---

### Task 4: Merge, fit, and generate the final PDF

**Files:**
- Use: `benchmarks/plot_operator_env_scaling.py`
- Create generated artifacts under: `benchmarks/results/operator_env_scaling/final/`

**Interfaces:**
- Consumes: completed raw CSV shards.
- Produces: merged raw CSV, summary CSV, fit CSV, and one three-panel PDF.

- [ ] **Step 1: Validate raw data before merging**

Require `quantity=local_effective_1site_apply_all_nodes`, all three publication methods, finite positive timings, and relative error below `1e-10`. Report missing or skipped method/size combinations rather than silently dropping them.

- [ ] **Step 2: Merge completed rows**

Keep only the newest complete repeat set for duplicate `(scaling_path, x value, method, repeat_id)` keys. Preserve raw rows in a generated merged CSV.

- [ ] **Step 3: Generate PDF-only publication output**

Run:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env conda run -p /software/cache/yuxiong/plot python benchmarks/plot_operator_env_scaling.py --raw benchmarks/results/operator_env_scaling/final/strict_three_variable_merged_raw.csv --output-prefix benchmarks/results/operator_env_scaling/final/strict_three_variable
```

- [ ] **Step 4: Verify outputs**

Run the two focused pytest files, `git diff --check`, and `pdfinfo` on the generated PDF. Confirm no publication PNG was generated.

