#!/usr/bin/env python3
"""Collect diagnostic snapshots and fit their observed power-law exponents."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from benchmarks.run_contraction_scaling_diagnostic import load_snapshot


KEY_FIELDS = (
    "panel",
    "kernel",
    "state_bond",
    "primitive_basis",
    "operator_bond",
    "contract_primitive",
)
METRICS = (
    "optimized_flops",
    "largest_intermediate",
    "allocation_sec",
    "expression_build_sec",
    "operator_build_sec",
    "environment_build_sec",
    "apply_sec",
    "time_total_sec",
    "state_tensor_elements",
    "operator_tensor_elements",
    "peak_memory_mb",
)
FIT_METRICS = (
    "optimized_flops",
    "apply_sec",
    "time_total_sec",
    "state_tensor_elements",
    "operator_tensor_elements",
)


def collect_snapshots(snapshot_dir):
    return [load_snapshot(path) for path in sorted(snapshot_dir.rglob("*.npz"))]


def summarize_repeats(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        groups[tuple(row[field] for field in KEY_FIELDS)].append(row)

    summary = []
    for key in sorted(groups, key=lambda value: tuple(str(item) for item in value)):
        group = groups[key]
        result = dict(zip(KEY_FIELDS, key))
        result["n_repeats"] = len(group)
        for metric in METRICS:
            values = [float(row[metric]) for row in group if metric in row]
            if not values:
                continue
            result[f"{metric}_median"] = statistics.median(values)
            result[f"{metric}_mean"] = statistics.mean(values)
            result[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(result)
    return summary


def _log_fit(points):
    xs = [math.log(float(x)) for x, _ in points]
    ys = [math.log(float(y)) for _, y in points]
    xmean = statistics.mean(xs)
    ymean = statistics.mean(ys)
    denominator = sum((x - xmean) ** 2 for x in xs)
    alpha = sum((x - xmean) * (y - ymean) for x, y in zip(xs, ys)) / denominator
    intercept = ymean - alpha * xmean
    residual = sum((y - (alpha * x + intercept)) ** 2 for x, y in zip(xs, ys))
    total = sum((y - ymean) ** 2 for y in ys)
    r2 = 1.0 if total == 0 else 1.0 - residual / total
    return round(alpha, 12), intercept, r2


def fit_scaling(summary):
    fits = []
    groups = defaultdict(list)
    for row in summary:
        groups[(row["panel"], row["kernel"], row["contract_primitive"])].append(row)

    for (panel, kernel, contract_primitive), rows in sorted(groups.items()):
        x_axis = "state_bond" if panel == "internal_ms" else "primitive_basis"
        for metric in FIT_METRICS:
            value_field = f"{metric}_median"
            points = sorted({
                (float(row[x_axis]), float(row[value_field]))
                for row in rows
                if float(row[x_axis]) > 0
                and value_field in row
                and float(row[value_field]) > 0
            })
            if len(points) < 2:
                continue
            windows = (("all", points), ("largest_four", points[-4:]))
            for window, selected in windows:
                if window == "largest_four" and len(points) <= 4:
                    continue
                alpha, intercept, r2 = _log_fit(selected)
                fits.append({
                    "panel": panel,
                    "kernel": kernel,
                    "contract_primitive": contract_primitive,
                    "x_axis": x_axis,
                    "metric": metric,
                    "fit_window": window,
                    "alpha": alpha,
                    "intercept_logC": intercept,
                    "r2": r2,
                    "n_points": len(selected),
                    "x_min": selected[0][0],
                    "x_max": selected[-1][0],
                })
    return fits


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as f:
        if not fields:
            return
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({
            key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        } for row in rows)


def _manifest_task_ids(path):
    with path.open(newline="") as f:
        return {int(row["task_id"]) for row in csv.DictReader(f, delimiter="\t")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    rows = collect_snapshots(args.snapshot_dir)
    summary = summarize_repeats(rows)
    fits = fit_scaling(summary)
    _write_csv(args.output_dir / "raw.csv", rows)
    _write_csv(args.output_dir / "summary.csv", summary)
    _write_csv(args.output_dir / "fits.csv", fits)

    ok_ids = {int(row["task_id"]) for row in rows if row.get("status") == "ok"}
    if args.manifest is not None:
        missing = sorted(_manifest_task_ids(args.manifest) - ok_ids)
        (args.output_dir / "missing_task_ids.json").write_text(
            json.dumps(missing, indent=2) + "\n"
        )
        print(f"Missing/error tasks: {len(missing)}")
    print(f"Collected {len(rows)} snapshots, {len(summary)} repeat groups, {len(fits)} fits")


if __name__ == "__main__":
    main()
