#!/usr/bin/env python3
"""Collect Hubbard-junction balanced snapshots and produce scaling artifacts."""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.hubbard_balanced_manifest import hubbard_balanced_tasks
from benchmarks.nature_plot_style import (
    METHOD_STYLES,
    finish_axis,
    label_panel,
    nature_style,
    save_pdf_png,
)
from benchmarks.run_hubbard_balanced_point import load_snapshot


FORMAL_METHODS = ("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")
REFERENCE_POWERS = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}


def collect_snapshots(snapshot_dir):
    return [load_snapshot(path) for path in sorted(Path(snapshot_dir).rglob("*.npz"))]


def missing_task_ids(rows, expected_ids):
    ok_ids = {int(row["task_id"]) for row in rows if row.get("status") == "ok"}
    return sorted(set(expected_ids) - ok_ids)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok" or row.get("method") not in FORMAL_METHODS:
            continue
        key = (int(row["n_lead"]), int(row["n_phonon"]), row["method"])
        groups[key].append(row)

    summary = []
    for key in sorted(groups):
        n_lead, n_phonon, method = key
        group = groups[key]
        totals = [float(row["time_total_sec"]) for row in group]
        envs = [float(row["time_env_build_sec"]) for row in group]
        applies = [float(row["time_apply_sec"]) for row in group]
        mems = [float(row["memory_peak_mb"]) for row in group]
        first = group[0]
        summary.append({
            "method": method,
            "n_lead": n_lead,
            "n_phonon": n_phonon,
            "n_total_sites": int(float(first["n_total_sites"])),
            "n_sop_terms": int(float(first["n_sop_terms"])),
            "n_active_nodes": int(float(first["n_active_nodes"])),
            "ttno_max_bond": int(float(first["ttno_max_bond"])),
            "state_max_bond": int(float(first["state_max_bond"])),
            "n_repeats": len(group),
            "time_total_mean_sec": statistics.mean(totals),
            "time_total_std_sec": statistics.stdev(totals) if len(totals) > 1 else 0.0,
            "time_env_build_mean_sec": statistics.mean(envs),
            "time_apply_mean_sec": statistics.mean(applies),
            "memory_peak_mean_mb": statistics.mean(mems),
            "relative_error_max_vs_ttno": max(float(row["relative_error_vs_ttno"]) for row in group),
        })
    return summary


def _fit(points):
    x = np.log(np.asarray([float(point["n_total_sites"]) for point in points]))
    y = np.log(np.asarray([float(point["time_total_mean_sec"]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(summary):
    fits = []
    for method in FORMAL_METHODS:
        points = sorted(
            (
                row for row in summary
                if row["method"] == method and row["time_total_mean_sec"] > 0
            ),
            key=lambda row: row["n_total_sites"],
        )
        if len(points) < 4:
            continue
        alpha, intercept, r2 = _fit(points[-4:])
        fits.append({
            "method": method,
            "x_axis": "n_total_sites",
            "fit_window": "largest_four",
            "alpha": alpha,
            "intercept_logC": intercept,
            "r2": r2,
            "n_points": 4,
            "x_min": points[-4]["n_total_sites"],
            "x_max": points[-1]["n_total_sites"],
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
    with nature_style():
        fig, ax = plt.subplots(figsize=(3.8, 2.8))
        fig.subplots_adjust(left=0.16, right=0.97, bottom=0.20, top=0.90)
        all_x = []
        for method in FORMAL_METHODS:
            points = sorted(
                (row for row in summary if row["method"] == method),
                key=lambda row: row["n_total_sites"],
            )
            if not points:
                continue
            x = np.asarray([float(row["n_total_sites"]) for row in points])
            y = np.asarray([float(row["time_total_mean_sec"]) for row in points])
            yerr = np.asarray([float(row["time_total_std_sec"]) for row in points])
            style = METHOD_STYLES[method]
            color = style["color"]
            ax.errorbar(x, y, yerr=yerr, capsize=2, label=method, **style)
            power = REFERENCE_POWERS[method]
            ref_y = y[-1] * (x / x[-1]) ** power
            ax.plot(x, ref_y, linestyle="--", color=color, alpha=0.7)
            ax.text(
                0.97,
                ref_y[-1],
                rf"$\propto N^{{{int(power)}}}$",
                transform=ax.get_yaxis_transform(),
                color=color,
                ha="right",
                va="center",
                clip_on=True,
            )
            all_x.extend(x.tolist())
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        if all_x:
            ax.set_xticks(sorted(set(all_x)))
            ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel("Total sites, $N = 4N_\\mathrm{lead}+2+N_\\mathrm{phonon}$")
        ax.set_ylabel("All-node local-action wall time (s)")
        label_panel(ax, "a", "Hubbard junction balanced")
        finish_axis(ax)
        ax.legend(loc="upper left", frameon=False)
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def generate(rows, output_prefix):
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    if not ok_rows:
        raise RuntimeError("no ok snapshots")
    summary = summarize(rows)
    fits = compute_fits(summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_hubbard_summary.csv"), summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_hubbard_fits.csv"), fits)
    pdf_path = output_prefix.with_name(output_prefix.name + "_hubbard_scaling.pdf")
    pdf, png = plot(summary, pdf_path)
    return summary, fits, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    rows = collect_snapshots(args.snapshot_dir)
    expected = {task.task_id for task in hubbard_balanced_tasks(repeats=3)}
    missing = missing_task_ids(rows, expected)
    if missing and not args.allow_partial:
        raise RuntimeError(f"refusing to label incomplete result as final: {sorted(missing)}")
    summary, fits, pdf, png = generate(rows, args.output_prefix)
    print(
        f"Collected {len(rows)}/{len(expected)} snapshots; "
        f"wrote {len(summary)} summary rows, {len(fits)} fits, "
        f"and figures {pdf} and {png}"
    )


if __name__ == "__main__":
    main()
