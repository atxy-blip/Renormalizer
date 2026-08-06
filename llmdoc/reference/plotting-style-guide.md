# Nature-style benchmark plotting reference

本参考页固定 formal operator-scaling 与 contraction diagnostics 图的可复现视觉
约定。它只记录呈现方式和 artifact 位置；图中的科学解释仍以
`llmdoc/overview/scaling-benchmark-status.md` 与
`llmdoc/architecture/primitive-contraction-scaling.md` 为准。

## Shared module and typography

所有正式 plotter 均通过 `benchmarks/nature_plot_style.py` 使用 scoped
`matplotlib.rc_context`，不得修改 process-wide rcParams。`NATURE_RCPARAMS` 的
精确值是：

```python
{
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "lines.markersize": 4.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}
```

`finish_axis()` supplies inward major ticks (length 4, width 0.8) and minor
ticks (length 2, width 0.6), including top and right ticks. `label_panel()`
uses left-aligned `(a)`, `(b)`, … titles.

## Formal method encodings and diagnostic palette

三个 formal 方法在所有 three-panel figures 中保持同一语义编码：

| method | label | color | marker |
| --- | --- | --- | --- |
| `sop_no_env` | SOP no env | `#00529B` | filled circle `o` |
| `sop_mctdh_like_state_env` | SOP strict state env | `#CC0000` | open circle `o` |
| `ttno_with_env` | TTNO + env | `#007A33` | filled square `s` |

The contraction diagnostics reuse blue `#00529B` for SOP, green `#007A33`
for contracted/TTNO paths, and red `#CC0000` for paired leaves/trees. Their
stage-specific series use orange `#d17a22` (operator construction), blue
`#3575a8` (environment construction), purple `#7655a8` (local actions), and
gray `#6b7280` (state storage). These colors identify a computation or
mechanism, not a new scientific ordering.

## Layout and export contract

- `benchmarks/plot_operator_env_scaling.py` and
  `benchmarks/plot_li2024_operator_scaling.py` use one row of three panels at
  `10.5 x 2.8` inches, with fixed margins `left=0.075`, `right=0.985`,
  `bottom=0.20`, `top=0.90`, and `wspace=0.10`.
- `benchmarks/plot_contraction_scaling_diagnostics.py` uses a two-by-two
  layout at `7.0 x 5.4` inches, with fixed margins `left=0.11`,
  `right=0.985`, `bottom=0.10`, `top=0.96`, `wspace=0.28`, and `hspace=0.34`.
- Do not call `tight_layout()`, constrained layout, or use
  `bbox_inches="tight"` for these figures. The explicit margins are part of
  the figure contract and protect labels, annotations, and the inset
  process-memory legend from clipping.
- `save_pdf_png()` writes a transparent PDF plus a transparent 300-dpi PNG at
  the same fixed boundary. PDF uses TrueType-compatible font embedding
  (`pdf.fonttype = 42`); PNG is the review/raster companion, not a separately
  cropped layout.

## Plotters, commands, and tracked artifacts

Use a writable temporary Matplotlib cache when regenerating. The formal
three-panel plotters write their summary and fit CSVs in addition to the PDF
and PNG; do not treat a rerun as permission to change the underlying science.

### Strict all-node operator-environment comparison

`benchmarks/plot_operator_env_scaling.py` aggregates the historical strict
all-node SOP/TTNO comparison into a three-panel figure. It remains the plotter
for that data group, but the required historical input
`benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_raw.csv`
is not tracked and is absent from this checkout. Therefore the historical
strict-all-node figure is currently not reproducible from repository contents,
and no runnable regeneration command is provided here. Its older output is not
one of the six tracked Nature-style artifacts below.

### Li.W.2024 formal three-panel figure

`benchmarks/plot_li2024_operator_scaling.py` regenerates the final
Li.W.2024 spin-boson figure:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -n reno-3.9 python -m benchmarks.plot_li2024_operator_scaling \
  --raw benchmarks/results/operator_env_scaling/li2024_formal/li2024_formal_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713
```

- `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf`
- `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png`

Main/SI split (2026-08-06):

- Main figure: only the `modes` panel draws the `N_b^3/N_b^2/N_b` guides and
  reports exponents. The `state_bond` and `primitive_basis` panels are
  robustness checks without power-law guides; each carries a vertical
  topology-switch line (`M_s=10` and `d=20`, respectively).
- SI figure: all three panels keep their largest-four fits and power-law
  guides (`M_s^4` for state bond, constant for large `d`). It is generated
  together with the main figure by the Slurm finalizer:

```text
benchmarks/results/operator_env_scaling/final/
  li2024_spin_boson_20260713_si_scaling_three_panel.pdf
  li2024_spin_boson_20260713_si_scaling_three_panel.png
```

The plot CLI (`python -m benchmarks.plot_li2024_operator_scaling ...`) defaults
to the main figure; SI output is produced by
`sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch`.

### Contraction diagnostics two-by-two figures

`benchmarks/plot_contraction_scaling_diagnostics.py` regenerates both
diagnostic figure groups:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -n reno-3.9 python -m benchmarks.plot_contraction_scaling_diagnostics \
  --summary benchmarks/results/operator_env_scaling/contraction_diagnostics/aggregate/summary.csv \
  --output-dir benchmarks/results/operator_env_scaling/contraction_diagnostics/figures
```

- `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf`
- `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png`
- `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf`
- `benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png`

Together, the Li main/SI pairs and these two diagnostic pairs are the eight
tracked Nature-style artifacts. The figures preserve the existing fitted
exponents and the distinction between optimized-FLOP complexity, isolated
kernel timing, and whole-workflow timing; presentation changes are not new
scaling claims.
