#!/usr/bin/env python3
"""Cost-metric analysis for the Hubbard balanced scan.

Reads the finalized Hubbard summary and reports, for every method:
per-sweep wall time (all-node local action), peak memory, memory x time product,
and relative error vs N. The first three are fitted over the largest four points.
"""

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.nature_plot_style import (
    METHOD_STYLES,
    finish_axis,
    label_panel,
    nature_style,
    save_pdf_png,
)


FORMAL_METHODS = ("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")
REFERENCE_POWERS = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}


def read_summary(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def compute_metrics(rows):
    metrics = []
    for row in rows:
        if row.get("method") not in FORMAL_METHODS:
            continue
        time_s = float(row["time_total_mean_sec"])
        mem_mb = float(row["memory_peak_mean_mb"])
        metrics.append({
            "method": row["method"],
            "n_lead": int(row["n_lead"]),
            "n_phonon": int(row["n_phonon"]),
            "n_total_sites": int(float(row["n_total_sites"])),
            "time_per_sweep_mean_sec": time_s,
            "time_per_sweep_std_sec": float(row["time_total_std_sec"]),
            "memory_peak_mean_mb": mem_mb,
            "memory_time_product_mb_s": time_s * mem_mb,
            "relative_error_max_vs_ttno": float(row["relative_error_max_vs_ttno"]),
        })
    return metrics


def _fit(points, field):
    x = np.log(np.asarray([float(point["n_total_sites"]) for point in points]))
    y = np.log(np.asarray([float(point[field]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(metrics):
    fits = []
    for method in FORMAL_METHODS:
        points = sorted(
            (
                row for row in metrics
                if row["method"] == method and row["time_per_sweep_mean_sec"] > 0
            ),
            key=lambda row: row["n_total_sites"],
        )
        if len(points) < 4:
            continue
        for field in ("time_per_sweep_mean_sec", "memory_peak_mean_mb", "memory_time_product_mb_s"):
            alpha, intercept, r2 = _fit(points[-4:], field)
            fits.append({
                "method": method,
                "metric": field,
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


def plot(metrics, pdf_path):
    panels = (
        ("time", "Per-sweep wall time (s)", "time_per_sweep_mean_sec", True),
        ("memory", "Peak memory (MB)", "memory_peak_mean_mb", False),
        ("memory_time", "Memory x time (MB s)", "memory_time_product_mb_s", False),
        ("error", "Relative error vs TTNO", "relative_error_max_vs_ttno", False),
    )
    with nature_style():
        fig, axes = plt.subplots(2, 2, figsize=(7.0, 5.4))
        fig.subplots_adjust(left=0.11, right=0.985, bottom=0.11, top=0.94, wspace=0.28, hspace=0.42)
        for ax, (name, ylabel, field, draw_guides) in zip(axes.ravel(), panels):
            all_x = []
            for method in FORMAL_METHODS:
                points = sorted(
                    (row for row in metrics if row["method"] == method),
                    key=lambda row: row["n_total_sites"],
                )
                if not points:
                    continue
                x = np.asarray([float(row["n_total_sites"]) for row in points])
                y = np.asarray([float(row[field]) for row in points])
                style = METHOD_STYLES[method]
                color = style["color"]
                ax.plot(x, y, label=method, **{k: v for k, v in style.items() if k != "color"})
                if draw_guides:
                    power = REFERENCE_POWERS[method]
                    ax.plot(x, y[-1] * (x / x[-1]) ** power, linestyle="--", color=color, alpha=0.7)
                all_x.extend(x.tolist())
            ax.set_xscale("log", base=2)
            if name != "error":
                ax.set_yscale("log")
            if all_x:
                ax.set_xticks(sorted(set(all_x)))
                ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlabel(r"Total sites, $N$")
            ax.set_ylabel(ylabel)
            label_panel(ax, chr(ord("a") + panels.index((name, ylabel, field, draw_guides))), name)
            finish_axis(ax)
        axes[0, 0].legend(loc="upper left", frameon=False)
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def generate(rows, output_prefix, figures_dir=None):
    metrics = compute_metrics(rows)
    fits = compute_fits(metrics)
    _write_csv(output_prefix.with_name(output_prefix.name + "_cost_summary.csv"), metrics)
    _write_csv(output_prefix.with_name(output_prefix.name + "_cost_fits.csv"), fits)
    if figures_dir is None:
        pdf_path = output_prefix.with_name(output_prefix.name + "_cost_metrics.pdf")
    else:
        pdf_path = Path(figures_dir) / "hubbard_cost_metrics.pdf"
    pdf, png = plot(metrics, pdf_path)
    return metrics, fits, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    args = parser.parse_args()
    metrics, fits, pdf, png = generate(
        read_summary(args.summary), args.output_prefix, args.figures_dir
    )
    print(
        f"Wrote {len(metrics)} metric rows, {len(fits)} fits, "
        f"and figures {pdf} and {png}"
    )


if __name__ == "__main__":
    main()
