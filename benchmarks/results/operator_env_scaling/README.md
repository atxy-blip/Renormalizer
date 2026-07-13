# Operator Environment Scaling Results

This directory separates the strict publication result from historical
benchmarks that measure different timing objects or intermediate algorithms.

## Final

`final/strict_all_nodes_medium_114336_raw.csv` is the source data for the
strict all-node comparison. Job 114336 used:

```text
scaling_path: lead_only
active_scope: all_nodes
n_total_sites: 18, 34, 66
repeats: 1
```

The publication plot contains only:

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

`sop_env_plus_operator_cache` remains in the raw CSV for provenance but is an
intermediate implementation path and is excluded from the figure.

Generate the final PDF with:

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -p /software/cache/yuxiong/plot \
python benchmarks/plot_operator_env_scaling.py \
  --raw benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336
```

The command also writes compact summary and fit CSV files. It does not produce
PNG output.

## Archive

- `archive/root_one_site_legacy/`: root-only local-action benchmarks.
- `archive/strict_all_nodes_development/`: strict baseline development runs,
  validation logs, and superseded diagnostic plots.
- `archive/legacy_sop_vs_ttno/`: original full-state SOP-vs-TTNO workflow.

