# Li.W.2024 Spin--Boson Operator Scaling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Submit a recoverable three-panel operator-kernel benchmark using the Li.W.2024 spin--boson model and adaptive binary primitive contraction.

**Architecture:** A deterministic manifest owns scientific parameters and topology selection. A focused point runner builds the spin--boson TTNS/TTNO/SOP case and writes one atomic snapshot. A separate finalizer aggregates only the new snapshot root and generates a Li-setup-specific PDF.

**Tech Stack:** Python 3.9, Renormalizer TTNS/TTNO/SOP, NumPy NPZ, Matplotlib, pytest, Slurm.

## Global Constraints

- Use the all-node one-site local effective-Hamiltonian action and name it explicitly.
- Use `d > M_s` as the only primitive-contraction condition.
- Keep old `ren_formal` data immutable.
- Use one CPU thread and atomic per-task snapshots.
- Keep state-bond and primitive-basis scans at or below 100 to avoid repeating the verified 128GB `M_s=300` OOM.

---

### Task 1: Manifest and topology contract

**Files:**
- Create: `benchmarks/li2024_formal_manifest.py`
- Create: `renormalizer/tn/tests/test_li2024_formal_benchmark.py`

- [x] Write tests for all 189 tasks, exact panel controls, and `d > M_s`.
- [x] Run the focused test and verify it fails because the module is absent.
- [x] Implement TSV serialization and strict boolean parsing.
- [x] Run the focused test and verify it passes.

### Task 2: Spin--boson point runner

**Files:**
- Create: `benchmarks/benchmark_li2024_operator_env.py`
- Create: `benchmarks/run_li2024_formal_point.py`
- Modify: `renormalizer/tn/tests/test_li2024_formal_benchmark.py`

- [x] Write failing builder, topology, metadata, and snapshot tests.
- [x] Verify the expected failures.
- [x] Implement the sub-Ohmic model, adaptive binary tree, selected-method action, and atomic NPZ output.
- [x] Verify a small SOP point agrees with its TTNO reference.

### Task 3: Finalizer and plot semantics

**Files:**
- Create: `benchmarks/plot_li2024_operator_scaling.py`
- Create: `benchmarks/finalize_li2024_formal.py`
- Modify: `renormalizer/tn/tests/test_li2024_formal_benchmark.py`

- [x] Write failing tests for repeat aggregation, missing-task reporting, and `M_s^4`/constant guides.
- [x] Implement CSV aggregation, fits, and three-panel PDF generation.
- [x] Run focused tests and a synthetic plot smoke test.

### Task 4: Slurm wrappers and submission

**Files:**
- Create: `benchmarks/scripts/curie_cpu_li2024_formal_array.sbatch`
- Create: `benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch`
- Generate: `benchmarks/results/operator_env_scaling/li2024_formal/manifest.tsv`

- [x] Test that conda activation precedes `set -u` and runners use module mode.
- [x] Run pytest, py_compile, shell syntax, manifest audit, and a small dry-run.
- [x] Submit the array and an `afterany` finalizer; record both job IDs.
