# SOP Debugging Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an executable, formula-linked Jupyter lab that teaches the current SOP, strict state-environment, and TTNO paths through concrete observations and a supervisor-ready recap.

**Architecture:** Keep the notebook as the learning interface and add one small Python support module for stable, testable inspection summaries. The support module exposes existing production objects without reimplementing their algorithms; notebook cells construct a tiny Li2024 case and inspect real `Op`, `SOPTerm`, environment-cache, TTNO, benchmark-row, and formal-output objects.

**Tech Stack:** Python 3.9, Jupyter notebook JSON, NumPy, Renormalizer TTNS/TTNO/SOP APIs, pytest, standard-library `json`.

## Global Constraints

- Use a deterministic Li.W.2024 spin--boson case with `n_modes=4`, `state_bond=2`, `primitive_basis=3`, and `contract_primitive=True`.
- Do not require Slurm, production-sized data generation, `ipdb`, `debugpy`, or a new package dependency.
- Keep optional debugger pauses behind `RUN_BREAKPOINTS = False`.
- The scientific timing identity is `local_effective_1site_apply_all_nodes`, not a complete TDVP propagation step and not full-state `H|psi>`.
- The formal comparison contains only `sop_no_env`, `sop_mctdh_like_state_env`, and `ttno_with_env`.
- `sop_env_plus_operator_cache` is explanatory only and must be identified as an optimized non-strict path.

---

## File Structure

- Create `benchmarks/sop_debugging_lab.py`: stable inspection helpers that summarize production objects without changing them.
- Create `notebooks/sop_debugging_lab.ipynb`: ten guided investigations, formulas, executable cells, answer prompts, and oral recap.
- Create `renormalizer/tn/tests/test_sop_debugging_lab.py`: helper and notebook structure/execution contract.
- Create `llmdoc/guides/sop-debugging-lab.md`: durable run instructions and scientific boundary.
- Modify `llmdoc/index.md`: add the guide to the operation-guide map.
- Modify `llmdoc/reference/key-files.md`: index the notebook and support module.

### Task 1: Stable Inspection Helpers

**Files:**
- Create: `benchmarks/sop_debugging_lab.py`
- Test: `renormalizer/tn/tests/test_sop_debugging_lab.py`

**Interfaces:**
- Consumes: `build_li2024_spin_boson_case()`, `SOPBaselineOperator`, `TTNO`, `SOPOneSiteEffective`, and `SOPMCTDHSweepEnvironment`.
- Produces:
  - `build_lab_case() -> dict`
  - `summarize_symbolic_terms(terms, sop) -> list[dict]`
  - `summarize_tree_local_ops(tree, sop_term) -> list[dict]`
  - `summarize_strict_cache(environment) -> dict`
  - `compare_cache_modes(sop, psi, active_node=None) -> dict`
  - `summarize_ttno(ttno) -> dict`

- [ ] **Step 1: Write failing helper-contract tests**

```python
from benchmarks.sop_debugging_lab import (
    build_lab_case,
    compare_cache_modes,
    summarize_strict_cache,
    summarize_symbolic_terms,
    summarize_tree_local_ops,
    summarize_ttno,
)


def test_lab_case_exposes_real_small_li2024_objects():
    ctx = build_lab_case()
    assert len(ctx["terms"]) == 13
    assert ctx["sop"].n_terms == 13
    assert max(ctx["psi"].bond_dims) == 2
    assert ctx["metadata"]["quantity"] == "local_effective_1site_apply_all_nodes"


def test_lab_summaries_make_term_and_cache_structure_observable():
    ctx = build_lab_case()
    terms = summarize_symbolic_terms(ctx["terms"], ctx["sop"])
    local = summarize_tree_local_ops(ctx["tree"], ctx["sop"].terms[-1])
    ctx["strict_env"].build_env_cache()
    strict = summarize_strict_cache(ctx["strict_env"])
    cache_comparison = compare_cache_modes(ctx["sop"], ctx["psi"])
    ttno = summarize_ttno(ctx["ttno"])

    assert terms[0]["symbol"] == "sigma_x"
    assert any(row["is_nontrivial"] for row in local)
    assert strict["key_shape"] == "(source_node_idx, target_node_idx, term_index)"
    assert strict["n_entries"] == 2 * (len(ctx["tree"].node_list) - 1) * ctx["sop"].n_terms
    assert cache_comparison["signature_entries"] <= cache_comparison["term_entries"]
    assert ttno["max_bond"] == max(ctx["ttno"].bond_dims)
```

- [ ] **Step 2: Run the tests and verify the missing-module failure**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_debugging_lab.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'benchmarks.sop_debugging_lab'`.

- [ ] **Step 3: Implement the inspection helpers**

Implement `build_lab_case()` with the real production constructors:

```python
def build_lab_case():
    tree, terms, psi = build_li2024_spin_boson_case(
        n_modes=4,
        state_bond=2,
        primitive_basis=3,
        contract_primitive=True,
    )
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    strict_env = SOPMCTDHSweepEnvironment(sop, psi)
    return {
        "tree": tree,
        "terms": terms,
        "psi": psi,
        "sop": sop,
        "ttno": ttno,
        "strict_env": strict_env,
        "active_nodes": list(psi.node_list),
        "metadata": {
            "case_name": "li2024_spin_boson",
            "n_modes": 4,
            "state_bond": 2,
            "primitive_basis": 3,
            "contract_primitive": True,
            "quantity": "local_effective_1site_apply_all_nodes",
        },
    }
```

Summaries must return built-in Python scalars, tuples, and lists so notebook
printing does not depend on pandas. `compare_cache_modes()` must build
`SOPOneSiteEffective` caches in `SOP_CACHE_TERM` and `SOP_CACHE_SIGNATURE`
modes on the same active node and report entry counts plus representative keys.

- [ ] **Step 4: Run focused helper tests**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_debugging_lab.py -q
```

Expected: both helper tests pass.

- [ ] **Step 5: Commit the helper layer**

```bash
git add benchmarks/sop_debugging_lab.py renormalizer/tn/tests/test_sop_debugging_lab.py
git commit -m "test: add SOP debugging inspection helpers"
```

### Task 2: Executable Ten-Investigation Notebook

**Files:**
- Create: `notebooks/sop_debugging_lab.ipynb`
- Modify: `renormalizer/tn/tests/test_sop_debugging_lab.py`

**Interfaces:**
- Consumes: all six public helper functions from Task 1 and the production
  functions named in the notebook breakpoint instructions.
- Produces: a valid notebook with metadata name `reno-3.9`, ten headings
  `Investigation 1` through `Investigation 10`, `RUN_BREAKPOINTS = False`, and
  a final `LAB_COMPLETE = True` executable marker.

- [ ] **Step 1: Add failing notebook structure and execution tests**

```python
import json
from pathlib import Path


NOTEBOOK = Path("notebooks/sop_debugging_lab.ipynb")


def _load_notebook():
    return json.loads(NOTEBOOK.read_text())


def test_notebook_contains_all_investigations_formulas_and_recap():
    notebook = _load_notebook()
    markdown = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )
    for number in range(1, 11):
        assert f"Investigation {number}" in markdown
    assert r"H = \\sum_l c_l" in markdown
    assert r"E_{l,u\\rightarrow v}" in markdown
    assert "What changed / Why / Effect" in markdown
    assert "local_effective_1site_apply_all_nodes" in markdown


def test_notebook_code_cells_execute_with_breakpoints_disabled():
    notebook = _load_notebook()
    namespace = {"__name__": "__sop_lab_test__"}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), str(NOTEBOOK), "exec"), namespace)
    assert namespace["RUN_BREAKPOINTS"] is False
    assert namespace["LAB_COMPLETE"] is True
```

- [ ] **Step 2: Run the notebook tests and verify failure**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_debugging_lab.py -q
```

Expected: failure because `notebooks/sop_debugging_lab.ipynb` does not exist.

- [ ] **Step 3: Create notebook setup and Investigations 1--5**

Create valid `nbformat=4` JSON. The setup cell must:

```python
from pathlib import Path
import inspect
import numpy as np

from benchmarks.sop_debugging_lab import (
    build_lab_case,
    compare_cache_modes,
    summarize_strict_cache,
    summarize_symbolic_terms,
    summarize_tree_local_ops,
    summarize_ttno,
)

RUN_BREAKPOINTS = False
ctx = build_lab_case()
tree, terms, psi = ctx["tree"], ctx["terms"], ctx["psi"]
sop, ttno = ctx["sop"], ctx["ttno"]
```

Investigations 1--5 must cover the pipeline map, `Op`/`SOPTerm`, tree-node
splitting, `BasisSet.op_mat()`, and `_apply_term_to_ttns()`. Each investigation
must include the approved eight-part learning structure and a code cell that
prints the exact object or shape named by its prompt.

- [ ] **Step 4: Add Investigations 6--10 and the oral recap**

Investigations 6--10 must build and summarize the strict environment, compare
cache modes, inspect TTNO tensors/bonds, run a small three-method point, and
trace one formal task. The small benchmark cell must use:

```python
from types import SimpleNamespace
from benchmarks.benchmark_li2024_operator_env import run_li2024_point

rows = run_li2024_point(
    panel="primitive_basis",
    n_modes=4,
    state_bond=2,
    primitive_basis=3,
    contract_primitive=True,
    repeat_id=0,
    args=SimpleNamespace(active_scope="all_nodes", timeout_sec=120, memory_limit_mb=0.0),
    git_commit="sop-debugging-lab",
)
assert {row["method"] for row in rows} == {
    "sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env"
}
assert max(row["relative_error_vs_ttno"] for row in rows) < 1e-10
```

The final cells must include the measured exponent recap from the spec, the
formula/code lookup, the modification/motivation/effect table, common mistakes,
blank Markdown answer prompts, and:

```python
LAB_COMPLETE = True
print("SOP debugging lab completed successfully.")
```

- [ ] **Step 5: Execute all notebook code through pytest**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_debugging_lab.py -q
```

Expected: all helper, structure, and notebook execution tests pass.

- [ ] **Step 6: Commit the notebook**

```bash
git add notebooks/sop_debugging_lab.ipynb renormalizer/tn/tests/test_sop_debugging_lab.py
git commit -m "docs: add executable SOP debugging lab"
```

### Task 3: Learning Guide and Final Notebook Verification

**Files:**
- Create: `llmdoc/guides/sop-debugging-lab.md`
- Modify: `llmdoc/index.md`
- Modify: `llmdoc/reference/key-files.md`

**Interfaces:**
- Consumes: the completed notebook and helper module.
- Produces: stable llmdoc routes containing the launch command, investigation
  map, breakpoint policy, formal-method boundary, and completed-result recap.

- [ ] **Step 1: Add the llmdoc guide**

Document:

- launch with `conda run -n reno-3.9 jupyter lab notebooks/sop_debugging_lab.ipynb`;
- `RUN_BREAKPOINTS=False` for uninterrupted execution and `True` only for the
  specifically marked cells;
- the ten-investigation sequence;
- the distinction among full-state SOP apply, all-node local actions, and full
  TDVP propagation;
- the three formal method labels and excluded operator-signature path;
- the three completed scaling conclusions from the design spec.

- [ ] **Step 2: Link the guide and key files**

Add one guide link to `llmdoc/index.md`. Add entries for
`notebooks/sop_debugging_lab.ipynb` and `benchmarks/sop_debugging_lab.py` to
`llmdoc/reference/key-files.md`.

- [ ] **Step 3: Run the complete learning-material test set**

Run:

```bash
conda run -n reno-3.9 python -m pytest \
  renormalizer/tn/tests/test_sop_debugging_lab.py \
  renormalizer/tn/tests/test_sop_baseline.py \
  renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py \
  renormalizer/tn/tests/test_li2024_formal_benchmark.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Run documentation and repository checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only the intended guide/index changes are
uncommitted.

- [ ] **Step 5: Commit the learning guide**

```bash
git add llmdoc/guides/sop-debugging-lab.md llmdoc/index.md llmdoc/reference/key-files.md
git commit -m "docs: explain the SOP debugging workflow"
```
