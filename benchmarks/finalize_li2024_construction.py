#!/usr/bin/env python3
"""Collect Li.W.2024 operator-construction snapshots and produce SI artifacts."""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.li2024_construction_manifest import (
    CONSTRUCTION_MODE_VALUES,
    CONSTRUCTION_PRIMITIVE_BASIS_VALUES,
    CONSTRUCTION_STATE_BOND_VALUES,
    construction_tasks,
)
from benchmarks.nature_plot_style import (
    METHOD_STYLES,
    finish_axis,
    label_panel,
    nature_style,
    save_pdf_png,
)
from benchmarks.run_li2024_construction_point import load_snapshot


BUILD_METHODS = ("sop", "ttno")


def collect_snapshots(snapshot_dir):
    return [load_snapshot(path) for path in sorted(Path(snapshot_dir).rglob("*.npz"))]


def missing_task_ids(rows, expected_ids):
    ok_ids = {int(row["task_id"]) for row in rows if row.get("status") == "ok"}
    return sorted(set(expected_ids) - ok_ids)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        key = (
            row["panel"],
            int(row["n_modes"]),
            int(row["state_bond"]),
            int(row["primitive_basis"]),
            bool(row["contract_primitive"]),
        )
        groups[key].append(row)

    summary = []
    for key in sorted(groups):
        panel, n_modes, state_bond, primitive_basis, contract_primitive = key
        group = groups[key]
        sop_times = [float(row["sop_build_time_sec"]) for row in group]
        ttno_times = [float(row["ttno_build_time_sec"]) for row in group]
        sop_mem = [float(row["sop_peak_memory_mb"]) for row in group]
        ttno_mem = [float(row["ttno_peak_memory_mb"]) for row in group]
        first = group[0]
        summary.append({
            "panel": panel,
            "n_modes": n_modes,
            "target_state_bond": state_bond,
            "primitive_basis_dim": primitive_basis,
            "contract_primitive": contract_primitive,
            "n_sop_terms": int(first["n_sop_terms"]),
            "ttno_max_bond": int(first["ttno_max_bond"]),
            "operator_tensor_elements": int(first["operator_tensor_elements"]),
            "n_repeats": len(group),
            "sop_build_time_mean_sec": statistics.mean(sop_times),
            "sop_build_time_std_sec": statistics.stdev(sop_times) if len(sop_times) > 1 else 0.0,
            "ttno_build_time_mean_sec": statistics.mean(ttno_times),
            "ttno_build_time_std_sec": statistics.stdev(ttno_times) if len(ttno_times) > 1 else 0.0,
            "sop_peak_memory_mean_mb": statistics.mean(sop_mem),
            "ttno_peak_memory_mean_mb": statistics.mean(ttno_mem),
        })
    return summary


def _fit(points, x_field, value_field):
    x = np.log(np.asarray([float(point[x_field]) for point in points]))
    y = np.log(np.asarray([float(point[value_field]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(summary):
    panels = (
        ("modes", "n_modes"),
        ("state_bond", "target_state_bond"),
        ("primitive_basis", "primitive_basis_dim"),
    )
    fits = []
    for panel_name, x_field in panels:
        for method in BUILD_METHODS:
            value_field = f"{method}_build_time_mean_sec"
            points = sorted(
                (
                    row for row in summary
                    if row["panel"] == panel_name and float(row[value_field]) > 0
                ),
                key=lambda row: float(row[x_field]),
            )
            if len(points) < 4:
                continue
            alpha, intercept, r2 = _fit(points[-4:], x_field, value_field)
            fits.append({
                "panel": panel_name,
                "method": method,
                "x_axis": x_field,
                "fit_window": "largest_four",
                "alpha": alpha,
                "intercept_logC": intercept,
                "r2": r2,
                "n_points": 4,
                "x_min": float(points[-4][x_field]),
                "x_max": float(points[-1][x_field]),
            })
    return fits


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot(summary, pdf_path):
    panels = (
        ("modes", "n_modes", r"Number of modes, $N_b$"),
        ("state_bond", "target_state_bond", r"State bond dimension, $M_s$"),
        ("primitive_basis", "primitive_basis_dim", r"Primitive basis, $d$"),
    )
    styles = {
        "sop": METHOD_STYLES["sop_no_env"],
        "ttno": METHOD_STYLES["ttno_with_env"],
    }
    labels = {"sop": "SOP baseline build", "ttno": "TTNO build"}
    with nature_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8), sharey=True)
        fig.subplots_adjust(left=0.075, right=0.985, bottom=0.20, top=0.90, wspace=0.10)
        for panel_index, (ax, (panel_name, x_field, xlabel)) in enumerate(zip(axes, panels)):
            all_x = []
            for method in BUILD_METHODS:
                value_field = f"{method}_build_time_mean_sec"
                error_field = f"{method}_build_time_std_sec"
                points = sorted(
                    (row for row in summary if row["panel"] == panel_name),
                    key=lambda row: float(row[x_field]),
                )
                if not points:
                    continue
                x = np.asarray([float(row[x_field]) for row in points])
                y = np.asarray([float(row[value_field]) for row in points])
                yerr = np.asarray([float(row[error_field]) for row in points])
                ax.errorbar(x, y, yerr=yerr, capsize=2, label=labels[method], **styles[method])
                all_x.extend(x.tolist())
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            if all_x:
                ax.set_xticks(sorted(set(all_x)))
                ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlabel(xlabel)
            label_panel(ax, chr(ord("a") + panel_index), panels[panel_index][0])
            finish_axis(ax)
        axes[0].set_ylabel("Operator build wall time (s)")
        axes[0].legend(loc="upper left", frameon=False)
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def generate(rows, output_prefix, figures_dir=None):
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    if not ok_rows:
        raise RuntimeError("no ok snapshots")
    summary = summarize(rows)
    fits = compute_fits(summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_construction_summary.csv"), summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_construction_fits.csv"), fits)
    if figures_dir is None:
        pdf_path = output_prefix.with_name(output_prefix.name + "_construction_scaling.pdf")
    else:
        pdf_path = Path(figures_dir) / "li2024_si_construction_scaling.pdf"
    pdf, png = plot(summary, pdf_path)
    return summary, fits, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    rows = collect_snapshots(args.snapshot_dir)
    expected = {task.task_id for task in construction_tasks(repeats=3)}
    missing = missing_task_ids(rows, expected)
    if missing and not args.allow_partial:
        raise RuntimeError(f"refusing to label incomplete result as final: {sorted(missing)}")
    summary, fits, pdf, png = generate(rows, args.output_prefix, figures_dir=args.figures_dir)
    print(
        f"Collected {len(rows)}/{len(expected)} snapshots; "
        f"wrote {len(summary)} summary rows, {len(fits)} fits, "
        f"and figures {pdf} and {png}"
    )


if __name__ == "__main__":
    main()
