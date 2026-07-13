# Ren-Style Formal Tree Scaling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Ren-style three-variable benchmark for the existing Tree SOP/TTNO algorithms with independent, recoverable NPZ snapshots.

**Architecture:** A deterministic manifest enumerates every `(panel, method, x, repeat)` task. A single-point runner invokes the existing all-node contraction kernels for one selected method, computes TTNO reference data when required, and atomically writes one JSON-backed NPZ. A Slurm array reads one manifest row per task.

**Tech Stack:** Python 3.9, NumPy NPZ, pytest, Slurm, Renormalizer TTNS/TTNO.

## Global Constraints

- Compare only the existing Tree methods: `sop_no_env`, `sop_mctdh_like_state_env`, `ttno_with_env`.
- Use `ACTIVE_SCOPE=all_nodes` and one CPU thread.
- Modes panel: `M_s=20`, `d=10`, seven `N_total_sites` points ending at 300.
- Bond panel: 16 phonon modes, `d=10`, scan `M_s` through 300.
- Primitive panel: 16 phonon modes, `M_s=20`, scan `d` through 100.
- Save every repeat as an independent atomic NPZ; do not require a final CSV.

---

### Task 1: Formal manifest

**Files:**
- Create: `benchmarks/ren_formal_manifest.py`
- Test: `renormalizer/tn/tests/test_ren_formal_benchmark.py`

- [ ] Write a failing test asserting the exact fixed parameters, point ranges, three methods, three repeats, and unique task IDs.
- [ ] Run the focused test and confirm it fails because the module does not exist.
- [ ] Implement `formal_tasks()` and TSV serialization.
- [ ] Run the focused test and confirm it passes.

### Task 2: Single-point NPZ runner

**Files:**
- Create: `benchmarks/run_ren_formal_point.py`
- Modify: `benchmarks/benchmark_adaptive_operator_env.py`
- Test: `renormalizer/tn/tests/test_ren_formal_benchmark.py`

- [ ] Write failing tests for method selection, distinct-x fit handling, and atomic JSON-backed NPZ round-trip.
- [ ] Run the tests and confirm the expected failures.
- [ ] Reuse `_run_point` with one selected method, retaining TTNO only as the numerical reference for SOP methods.
- [ ] Write snapshots to a temporary NPZ and atomically replace the final path.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Slurm array submission

**Files:**
- Create: `benchmarks/scripts/curie_cpu_ren_formal_array.sbatch`
- Generate: `benchmarks/results/operator_env_scaling/ren_formal/manifest.tsv`

- [ ] Validate Python compilation, pytest, and shell syntax.
- [ ] Generate the manifest and count all rows.
- [ ] Submit one array with one task per manifest row and bounded concurrency.
- [ ] Record the job ID and exact parameter ranges in the run README and llmdoc.

