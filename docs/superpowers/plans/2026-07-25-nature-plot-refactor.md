# Nature Plot Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor all current formal scaling figures onto one tested Nature-style system and regenerate consistent PDF and PNG outputs without changing data aggregation, fits, or scientific claims.

**Architecture:** Add a focused shared Matplotlib style/export module and keep data preparation inside the existing three plotters. Each plotter receives only presentation changes plus a second PNG output; existing summary and fit functions remain untouched and are protected by current tests.

**Tech Stack:** Python 3.9, Matplotlib, NumPy, pytest, Poppler `pdftoppm` for visual review.

## Global Constraints

- Use Arial, Helvetica, then DejaVu Sans fallback; set PDF/PS font type to 42.
- Use 8 pt base/axis/tick text, 9 pt panel titles, 7 pt legends, 0.8 pt axes/ticks, 1.2 pt lines, and 4--4.5 pt markers.
- Ticks point inward and top/right ticks are enabled.
- Final PDF exports use fixed margins, transparent backgrounds, and no `bbox_inches="tight"`.
- PNG previews use 300 dpi.
- Formal method colors are blue `#00529B` for no-environment SOP, red `#CC0000` for strict SOP state environment, and green `#007A33` for TTNO.
- Color is not the only method encoding.
- Do not change CSV parsing, summary rows, fit windows, fit values, method inclusion rules, quantity validation, raw NPZ files, or raw CSV files.

---

## File Structure

- Create `benchmarks/nature_plot_style.py`: shared constants, rc context, axis finishing, panel labeling, and paired PDF/PNG export.
- Create `renormalizer/tn/tests/test_nature_plot_style.py`: shared style and export contract.
- Modify `benchmarks/plot_li2024_operator_scaling.py`: compact three-panel Nature layout and paired output.
- Modify `benchmarks/plot_operator_env_scaling.py`: same formal method encoding and paired output.
- Modify `benchmarks/plot_contraction_scaling_diagnostics.py`: two compact two-by-two figures.
- Modify existing plot tests: output and semantic encoding assertions.
- Create `llmdoc/reference/plotting-style-guide.md`: repository-specific plotting contract.
- Modify `llmdoc/index.md`, `llmdoc/reference/key-files.md`, and `llmdoc/overview/scaling-benchmark-status.md`.
- Regenerate the three current formal figure groups under `benchmarks/results/operator_env_scaling/`.

### Task 1: Shared Nature Style and Export Contract

**Files:**
- Create: `benchmarks/nature_plot_style.py`
- Create: `renormalizer/tn/tests/test_nature_plot_style.py`

**Interfaces:**
- Produces:
  - `NATURE_RCPARAMS: dict`
  - `METHOD_STYLES: dict[str, dict]`
  - `nature_style() -> matplotlib.rc_context`
  - `finish_axis(ax, *, minor=True) -> None`
  - `label_panel(ax, label: str, title: str) -> None`
  - `save_pdf_png(fig, pdf_path: Path, *, dpi: int = 300) -> tuple[Path, Path]`

- [ ] **Step 1: Write failing shared-style tests**

```python
import matplotlib.pyplot as plt

from benchmarks.nature_plot_style import (
    METHOD_STYLES,
    NATURE_RCPARAMS,
    nature_style,
    save_pdf_png,
)


def test_nature_style_matches_repository_contract():
    assert NATURE_RCPARAMS["font.sans-serif"] == ["Arial", "Helvetica", "DejaVu Sans"]
    assert NATURE_RCPARAMS["pdf.fonttype"] == 42
    assert NATURE_RCPARAMS["font.size"] == 8
    assert NATURE_RCPARAMS["axes.linewidth"] == 0.8
    assert NATURE_RCPARAMS["lines.linewidth"] == 1.2
    assert NATURE_RCPARAMS["xtick.direction"] == "in"
    assert NATURE_RCPARAMS["xtick.top"] is True
    assert METHOD_STYLES["sop_no_env"]["color"] == "#00529B"
    assert METHOD_STYLES["sop_mctdh_like_state_env"]["color"] == "#CC0000"
    assert METHOD_STYLES["ttno_with_env"]["color"] == "#007A33"


def test_save_pdf_png_writes_both_fixed_boundary_outputs(tmp_path):
    with nature_style():
        fig, ax = plt.subplots(figsize=(3.5, 2.8))
        ax.plot([1, 2], [1, 2])
        pdf, png = save_pdf_png(fig, tmp_path / "figure.pdf")
    assert pdf.name == "figure.pdf"
    assert png.name == "figure.png"
    assert pdf.stat().st_size > 0
    assert png.stat().st_size > 0
```

- [ ] **Step 2: Run tests and verify missing-module failure**

Run:

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_nature_plot_style.py -q
```

Expected: collection fails because `benchmarks.nature_plot_style` does not
exist.

- [ ] **Step 3: Implement the shared style**

Define `NATURE_RCPARAMS` with every exact value from Global Constraints.
`nature_style()` returns `matplotlib.rc_context(NATURE_RCPARAMS)`.
`finish_axis()` calls:

```python
ax.tick_params(which="major", direction="in", length=4, width=0.8, top=True, right=True)
ax.tick_params(which="minor", direction="in", length=2, width=0.6, top=True, right=True)
if minor:
    ax.minorticks_on()
```

`label_panel()` renders a left-aligned `f"({label}) {title}"` title.
`save_pdf_png()` creates the parent directory and calls:

```python
fig.savefig(pdf_path, format="pdf", transparent=True)
fig.savefig(png_path, format="png", dpi=dpi, transparent=True)
```

It must not pass `bbox_inches`.

- [ ] **Step 4: Run shared-style tests**

Run the Task 1 pytest command again.

Expected: both tests pass.

- [ ] **Step 5: Commit the shared module**

```bash
git add benchmarks/nature_plot_style.py renormalizer/tn/tests/test_nature_plot_style.py
git commit -m "feat: add shared Nature plot style"
```

### Task 2: Formal Three-Panel Plotters

**Files:**
- Modify: `benchmarks/plot_li2024_operator_scaling.py:22-47,179-258`
- Modify: `benchmarks/finalize_li2024_formal.py:48-79`
- Modify: `benchmarks/plot_operator_env_scaling.py:30-46,359-429`
- Modify: `renormalizer/tn/tests/test_li2024_formal_benchmark.py`
- Modify: `renormalizer/tn/tests/test_operator_env_scaling_plot.py`

**Interfaces:**
- Consumes: `METHOD_STYLES`, `nature_style()`, `finish_axis()`,
  `label_panel()`, and `save_pdf_png()`.
- Produces:
  - Li plot `plot(...) -> tuple[Path, Path]`
  - Li generation `generate(...) -> tuple[list, list, Path, Path]`
  - Li finalizer output reporting for both PDF and PNG paths
  - Ren plot `plot_publication_time(...) -> tuple[Path, Path]`

- [ ] **Step 1: Add failing output and style tests**

Extend the Li plot test with synthetic rows for every panel/method and assert:

```python
summary, fits, pdf, png = generate(rows, tmp_path / "li2024")
assert pdf.name == "li2024_scaling_three_panel.pdf"
assert png.name == "li2024_scaling_three_panel.png"
assert pdf.stat().st_size > 0
assert png.stat().st_size > 0
```

Extend the Ren plot test to assert that `METHOD_COLORS` equals the shared
blue/red/green mapping and that `plot_publication_time()` returns nonempty PDF
and PNG paths.

- [ ] **Step 2: Run focused tests and verify failures**

Run:

```bash
conda run -n reno-3.9 python -m pytest \
  renormalizer/tn/tests/test_nature_plot_style.py \
  renormalizer/tn/tests/test_li2024_formal_benchmark.py \
  renormalizer/tn/tests/test_operator_env_scaling_plot.py -q
```

Expected: failures because both plotters return only PDF output and still use
the old method palette.

- [ ] **Step 3: Refactor the Li2024 plot**

Wrap figure creation in `with nature_style():`. Use `figsize=(10.5, 2.8)` and:

```python
fig.subplots_adjust(left=0.075, right=0.985, bottom=0.20, top=0.90, wspace=0.10)
```

Use shared method colors plus filled-circle/open-circle/filled-square markers.
Retain error bars and reference powers. Remove the dense grids and suptitle.
Use `label_panel()` for `(a) Mode number`, `(b) State bond`, and `(c) Primitive
basis`. Place guide labels with right alignment at `0.97` of the x-axis span so
they cannot cross the fixed boundary. Return both paths from `save_pdf_png()`.

- [ ] **Step 4: Refactor the Ren formal plot**

Apply the same size, method styles, fixed margins, panel hierarchy, and paired
export. Preserve `SCALING_PANELS`, `REFERENCE_ALPHA`, path selection, reference
curve calculations, and publication-input validation exactly.

- [ ] **Step 5: Update the Li finalizer return contract**

Change the finalizer unpacking to:

```python
summary, fits, pdf, png = generate(rows, args.output_prefix)
```

and report both figure paths in its completion message. Do not change snapshot
collection, missing-task detection, or raw CSV writing.

- [ ] **Step 6: Run the formal plot tests**

Run the Task 2 pytest command again.

Expected: all tests pass.

- [ ] **Step 7: Commit the formal plot refactor**

```bash
git add \
  benchmarks/plot_li2024_operator_scaling.py \
  benchmarks/finalize_li2024_formal.py \
  benchmarks/plot_operator_env_scaling.py \
  renormalizer/tn/tests/test_li2024_formal_benchmark.py \
  renormalizer/tn/tests/test_operator_env_scaling_plot.py
git commit -m "feat: restyle formal scaling figures"
```

### Task 3: Contraction Diagnostic Figures

**Files:**
- Modify: `benchmarks/plot_contraction_scaling_diagnostics.py:37-334`
- Modify: `renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py`

**Interfaces:**
- Consumes: shared Nature helpers from Task 1.
- Produces: the existing five paths from `generate_figures()`, with unchanged
  filenames and fit records.

- [ ] **Step 1: Add failing semantic-style assertions**

Extend the diagnostic tests:

```python
from benchmarks.plot_contraction_scaling_diagnostics import COLORS


def test_diagnostic_palette_uses_nature_semantics():
    assert COLORS["sop"] == "#00529B"
    assert COLORS["ttno"] == "#007A33"
    assert COLORS["paired"] == "#CC0000"
```

Keep the existing five-artifact and `largest_four` assertions unchanged.

- [ ] **Step 2: Run the focused diagnostic tests**

Run:

```bash
conda run -n reno-3.9 python -m pytest \
  renormalizer/tn/tests/test_nature_plot_style.py \
  renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py -q
```

Expected: palette assertion fails against the old colors.

- [ ] **Step 3: Refactor complexity validation**

Use `with nature_style():`, `figsize=(7.0, 5.4)`, and:

```python
fig.subplots_adjust(left=0.11, right=0.985, bottom=0.10, top=0.96, wspace=0.28, hspace=0.34)
```

Remove `constrained_layout=True`, dense grids, and `bbox_inches`. Preserve the
four data panels, fit recording, reference powers, and uncertainty values.
Format legend fit labels as `label + rf" ($\\alpha_{{tail}}={value:.2f}$)"`.
Use shared axis finishing and paired export.

- [ ] **Step 4: Refactor model mechanism**

Use the same two-by-two dimensions and margins. Encode paired versus contracted
by red circles versus green squares. Encode TTNO storage with solid lines and
TTNS storage with dotted lines. Keep orange/blue/purple decomposition colors
for construction/environment/local action, with distinct markers.

- [ ] **Step 5: Run diagnostic tests**

Run the Task 3 pytest command again.

Expected: all tests pass and all five generated artifacts remain nonempty.

- [ ] **Step 6: Commit diagnostic figures**

```bash
git add \
  benchmarks/plot_contraction_scaling_diagnostics.py \
  renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py
git commit -m "feat: restyle contraction diagnostic figures"
```

### Task 4: Regenerate and Visually Audit All Formal Outputs

**Files:**
- Modify generated outputs under:
  - `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf`
  - `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png`
  - `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf`
  - `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png`
  - `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf`
  - `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png`

**Interfaces:**
- Consumes: completed plotters and the existing tracked raw/summary CSV data.
- Produces: publication PDFs and review PNGs at stable output stems.

- [ ] **Step 1: Preserve fit tables for the no-science-change check**

Run:

```bash
cp benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_fits.csv \
  /tmp/li2024_fits_before.csv
cp benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/plot_fits.csv \
  /tmp/diagnostic_fits_before.csv
```

Expected: both `/tmp` copies exist and are nonempty.

- [ ] **Step 2: Regenerate the Li2024 figure**

Run:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -n reno-3.9 python -m benchmarks.plot_li2024_operator_scaling \
  --raw benchmarks/results/operator_env_scaling/li2024_formal/li2024_formal_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713
```

Expected: summary CSV, fits CSV, PDF, and PNG are written.

- [ ] **Step 3: Regenerate both diagnostic figures**

Run:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -n reno-3.9 python -m benchmarks.plot_contraction_scaling_diagnostics \
  --summary benchmarks/results/operator_env_scaling/contraction_diagnostics/aggregate/summary.csv \
  --output-dir benchmarks/results/operator_env_scaling/contraction_diagnostics/figures
```

Expected: two PDFs, two PNGs, and `plot_fits.csv` are written.

- [ ] **Step 4: Confirm fit tables did not change**

Compare the preserved tables with the regenerated tables:

```bash
diff -u /tmp/li2024_fits_before.csv benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_fits.csv
diff -u /tmp/diagnostic_fits_before.csv benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/plot_fits.csv
```

Expected: both commands produce no diff.

- [ ] **Step 5: Render PDFs for visual inspection**

Run:

```bash
pdftoppm -png -f 1 -singlefile -r 160 \
  benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf \
  /tmp/li2024-nature
pdftoppm -png -f 1 -singlefile -r 160 \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf \
  /tmp/complexity-nature
pdftoppm -png -f 1 -singlefile -r 160 \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf \
  /tmp/mechanism-nature
```

Inspect all three images. Acceptance requires no clipping, no guide text beyond
the axes, readable 8 pt text, distinguishable grayscale markers, compact
frameless legends, and balanced panel whitespace.

- [ ] **Step 6: Commit regenerated artifacts**

```bash
git add -f \
  benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf \
  benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf \
  benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png
git commit -m "results: regenerate Nature-style scaling figures"
```

### Task 5: Plotting Documentation and Final Verification

**Files:**
- Create: `llmdoc/reference/plotting-style-guide.md`
- Modify: `llmdoc/index.md`
- Modify: `llmdoc/reference/key-files.md`
- Modify: `llmdoc/overview/scaling-benchmark-status.md`

**Interfaces:**
- Consumes: all completed plotting code and artifacts.
- Produces: stable documentation of dimensions, typography, semantic palette,
  export policy, figure locations, and unchanged scientific interpretation.

- [ ] **Step 1: Write the plotting reference**

Record the shared module, exact rc values, three formal method encodings,
three-panel and two-by-two dimensions, fixed-margin/no-tight-export rule, PDF
and PNG policy, and the command used to regenerate each figure group.

- [ ] **Step 2: Update llmdoc navigation and status**

Link the reference from `llmdoc/index.md`. Add the shared module and three
plotter roles to `llmdoc/reference/key-files.md`. Update
`llmdoc/overview/scaling-benchmark-status.md` to identify the Nature-style
artifacts while preserving all current exponents and scientific caveats.

- [ ] **Step 3: Run the complete focused test suite**

Run:

```bash
conda run -n reno-3.9 python -m pytest \
  renormalizer/tn/tests/test_nature_plot_style.py \
  renormalizer/tn/tests/test_li2024_formal_benchmark.py \
  renormalizer/tn/tests/test_operator_env_scaling_plot.py \
  renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py \
  renormalizer/tn/tests/test_sop_debugging_lab.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Verify repository state**

Run:

```bash
git diff --check
git status --short
git log --oneline --decorate --max-count=8
```

Expected: no whitespace errors; only intended llmdoc edits remain before the
final documentation commit.

- [ ] **Step 5: Commit plotting documentation**

```bash
git add \
  llmdoc/reference/plotting-style-guide.md \
  llmdoc/index.md \
  llmdoc/reference/key-files.md \
  llmdoc/overview/scaling-benchmark-status.md
git commit -m "docs: document Nature-style benchmark figures"
```
