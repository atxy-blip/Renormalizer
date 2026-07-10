# Strict Operator Scaling Figure Design

## Goal

Produce one publication-facing PDF that directly tests the expected all-node
scaling hierarchy:

```text
SOP no env             ~ N_site^3
SOP strict state env   ~ N_site^2
TTNO with env          ~ N_site
```

At the same time, reorganize previous benchmark scripts and outputs so that
legacy root-only results and implementation-stage diagnostics cannot be
mistaken for the final strict baseline.

## Final Figure

The final figure uses the completed `medium_114336` all-node, lead-only run.
Its horizontal axis is `N_total_sites`, and its vertical axis is mean total
wall time in seconds. Both axes use logarithmic scales.

Only these methods appear:

- `sop_no_env`
- `sop_mctdh_like_state_env`
- `ttno_with_env`

`sop_env_plus_operator_cache` remains available in archived raw data but is
excluded from the figure because it is an intermediate implementation path,
not one of the three theoretical baselines.

Each method is shown as colored scatter points. The legend reports its fitted
`alpha` against `N_total_sites`. Three dashed reference lines, anchored at the
geometric center of their corresponding data series, show slopes `alpha=3`,
`alpha=2`, and `alpha=1`. They are labeled as theoretical slope references,
not fitted curves.

The plotting command produces PDF only. No PNG is generated.

## Result Layout

The active result tree is organized by meaning:

```text
benchmarks/results/operator_env_scaling/
  README.md
  final/
    strict_all_nodes_medium_114336_raw.csv
    strict_all_nodes_medium_114336_summary.csv
    strict_all_nodes_medium_114336_fits.csv
    strict_all_nodes_scaling_vs_nsite.pdf
  archive/
    root_one_site_legacy/
    strict_all_nodes_development/
    legacy_sop_vs_ttno/
```

Each archive category contains a manifest describing its timing object,
algorithm identity, relevant Slurm job IDs, and why those results are not the
final figure source. Related Slurm logs move with the corresponding runs.

The active `benchmarks/` root retains only the strict adaptive benchmark,
final plotting entry point, current Slurm wrapper, and validation wrapper.
Earlier SOP-vs-TTNO scripts and notebook-generation utilities move under the
legacy archive without changing their contents.

## Data Handling

The original `medium_114336_raw.csv` is preserved by moving it into the final
directory under a descriptive name. Summary and fit tables are regenerated
from that raw input. Existing historical outputs are moved, not deleted.

The final figure generator validates that the input contains
`quantity=local_effective_1site_apply_all_nodes` and all three required methods.
It ignores the operator-cache rows for publication output.

## Verification

Verification consists of:

1. Python compilation of the plotting script.
2. A focused plotting test for method filtering and reference-line slopes.
3. Regeneration of summary, fit, and PDF outputs from the archived raw input.
4. Inspection of the PDF rendering and confirmation that no PNG was created.
5. A manifest check ensuring every pre-existing benchmark result and log is
   either in `final/` or one of the three archive categories.

