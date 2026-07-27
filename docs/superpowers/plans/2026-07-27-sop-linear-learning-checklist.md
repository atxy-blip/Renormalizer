# SOP Linear Learning Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and index a 12-session, 45-minute, checkbox-driven SOP learning guide that ends in a supervisor-ready explanation of the implementation, experiments, and paper figures.

**Architecture:** One stable llmdoc guide owns the complete linear workflow. Existing notebook investigations, benchmark results, and plotting references remain the sources of truth; the guide links to them and adds sequencing, evidence gates, oral prompts, and stop rules without duplicating implementation.

**Tech Stack:** Markdown, llmdoc navigation, Jupyter notebook, Git, shell-based link/content validation.

## Global Constraints

- Use exactly 12 strictly ordered sessions of 45 minutes each.
- Each session uses `5 + 25 + 10 + 5` minutes for recall, execution, written evidence, and oral explanation.
- A session is complete only when its objective evidence is recorded.
- Preserve the exact method labels `sop_no_env`, `sop_mctdh_like_state_env`, and `ttno_with_env`.
- Distinguish full-state `H|psi>`, `local_effective_1site_apply_all_nodes`, and full TDVP propagation.
- Distinguish finite-window wall-time exponents from tensor FLOP complexity.
- Recommend the Li.W.2024 three-panel PDF for the main text and the two contraction-diagnostic PDFs for Supporting Information.
- Submission links point to PDF; PNG links are explicitly marked as previews.
- Do not present the partial Hubbard-junction or unreproducible historical strict-all-node figures as final paper figures.

---

### Task 1: Create the linear learning guide

**Files:**
- Create: `llmdoc/guides/sop-linear-learning-checklist.md`

**Interfaces:**
- Consumes: `notebooks/sop_debugging_lab.ipynb`, `llmdoc/guides/sop-debugging-lab.md`, `llmdoc/overview/scaling-benchmark-status.md`, and `llmdoc/reference/plotting-style-guide.md`.
- Produces: A single user-facing checklist with 12 sequential sessions and clickable paper-figure links.

- [ ] **Step 1: Write the guide header and operating rules**

Include:

- the one-session-only rule;
- the `5 + 25 + 10 + 5` minute structure;
- the Jupyter kernel registration and launch commands;
- a blank “current session” field;
- the 10-minute stuck rule;
- the rule that execution without recorded evidence cannot be checked off.

- [ ] **Step 2: Write Sessions 1–4**

Map setup and Investigations 1–4 to:

1. environment and experiment map;
2. `Op` and `SOPTerm`;
3. `dof2idx` tree localization;
4. `BasisSet.op_mat()` numeric matrices.

Each session must include:

- one top-level checkbox;
- exact notebook section;
- actions for each time slice;
- concrete variables or output to inspect;
- one written answer;
- one evidence gate;
- a three-sentence oral template;
- a stop rule.

- [ ] **Step 3: Write Sessions 5–8**

Map Investigations 5–8 to:

5. full 13-term no-environment apply;
6. strict directed-edge state environment;
7. term cache versus signature cache, including `91 → 33`;
8. TTNO operator-bond and environment reuse.

Keep `sop_env_plus_operator_cache` explicitly labeled optimized, explanatory, and non-strict.

- [ ] **Step 4: Write Sessions 9–10**

Session 9 records:

- all three formal method labels;
- all `status=ok`;
- relative-error interpretation;
- the exact quantity `local_effective_1site_apply_all_nodes`.

Session 10 records the real data chain:

```text
189 manifest tasks → 189 snapshots → 63 summary rows → 18 fits → PDF + PNG
```

- [ ] **Step 5: Write Session 11**

Include clickable links and panel-reading prompts for:

- main text: `li2024_spin_boson_20260713_scaling_three_panel.pdf`;
- SI Figure S1: `complexity_validation.pdf`;
- SI Figure S2: `model_mechanism.pdf`;
- all three PNG preview companions.

Require one sentence per panel and explicit statements of the wall-time/FLOP boundary.

- [ ] **Step 6: Write Session 12 and final oral rubric**

Require a 5–8 minute explanation in this order:

```text
problem → modification → reason → mechanism → measured effect → scientific boundary
```

Add a self-scored rubric and likely supervisor follow-up questions. Completion requires explaining the work without reading the notebook recap.

- [ ] **Step 7: Add the overall progress table**

Add one row per session with:

- completion checkbox;
- session title;
- required evidence;
- date;
- remaining question.

- [ ] **Step 8: Validate the guide**

Run:

```bash
rg -n '^## Session [0-9]+|^- \[ \] Session' \
  llmdoc/guides/sop-linear-learning-checklist.md
```

Expected:

- exactly 12 session headings;
- exactly 12 top-level session checkboxes.

Run:

```bash
rg -n 'sop_no_env|sop_mctdh_like_state_env|ttno_with_env|189|63|18|91|33|local_effective_1site_apply_all_nodes' \
  llmdoc/guides/sop-linear-learning-checklist.md
```

Expected: every required method label, quantity, and data-count checkpoint is present.

- [ ] **Step 9: Commit Task 1**

```bash
git add llmdoc/guides/sop-linear-learning-checklist.md
git commit -m "docs: add linear SOP learning checklist"
```

### Task 2: Index and verify the guide

**Files:**
- Modify: `llmdoc/index.md`
- Modify: `llmdoc/reference/key-files.md`

**Interfaces:**
- Consumes: `llmdoc/guides/sop-linear-learning-checklist.md`.
- Produces: Discoverable llmdoc navigation and a clean committed documentation state.

- [ ] **Step 1: Add the guide to llmdoc navigation**

In `llmdoc/index.md`, add the checklist under “操作指南”, immediately after the SOP debugging lab.

In `llmdoc/reference/key-files.md`, add the checklist beside `notebooks/sop_debugging_lab.ipynb` and describe it as the 12-session evidence-gated learning route.

- [ ] **Step 2: Verify every referenced artifact exists**

Run:

```bash
test -f notebooks/sop_debugging_lab.ipynb
test -f benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf
test -f benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png
test -f benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf
test -f benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png
test -f benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf
test -f benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png
```

Expected: every command exits 0.

- [ ] **Step 3: Verify Markdown and Git cleanliness**

Run:

```bash
git diff --check
rg -n 'sop-linear-learning-checklist' llmdoc/index.md llmdoc/reference/key-files.md
git status --short
```

Expected:

- no whitespace errors;
- both navigation files reference the new guide;
- only the intended documentation files are modified.

- [ ] **Step 4: Commit Task 2**

```bash
git add llmdoc/index.md llmdoc/reference/key-files.md
git commit -m "docs: index SOP learning checklist"
```

- [ ] **Step 5: Final verification**

Run the Task 1 content checks, Task 2 artifact checks, and:

```bash
git diff --check HEAD~2..HEAD
git status --short
```

Expected: all checks pass and the working tree is clean.

