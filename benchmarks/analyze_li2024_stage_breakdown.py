#!/usr/bin/env python3
"""Analyze existing Li.W.2024 snapshots for stage/memory/throughput SI evidence.

This is a derivation job, not a new benchmark: it consumes the already
collected 189 formal snapshots and reports, on the modes panel only,
per-stage wall-time exponents, peak-memory scaling, and a throughput proxy
(state tensor elements processed per second of apply time).
"""

import argparse
import csv
import statistics
from collections import defaultdict
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
TIME_METRICS = ("time_total_sec", "time_env_build_sec", "time_apply_sec")
ALL_METRICS = TIME_METRICS + ("memory_peak_mb", "elements_per_apply_second")
METRIC_FIELDS = {
    "time_total_sec": "time_total_mean_sec",
    "time_env_build_sec": "time_env_build_mean_sec",
    "time_apply_sec": "time_apply_mean_sec",
    "memory_peak_mb": "memory_peak_mean_mb",
    "elements_per_apply_second": "elements_per_apply_second",
}


def read_raw(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def summarize_modes(rows):
    groups = defaultdict(list)
    for row in rows:
        if (
            row.get("status") != "ok"
            or row.get("panel") != "modes"
            or row.get("method") not in FORMAL_METHODS
        ):
            continue
        key = (row["method"], int(row["n_modes"]))
        groups[key].append(row)

    summary = []
    for (method, n_modes), group in sorted(groups.items()):
        totals = [float(row["time_total_sec"]) for row in group]
        envs = [float(row["time_env_build_sec"]) for row in group]
        applies = [float(row["time_apply_sec"]) for row in group]
        mems = [float(row["memory_peak_mb"]) for row in group]
        state_elements = int(float(group[0]["state_tensor_elements"]))
        apply_mean = statistics.mean(applies)
        first = group[0]
        summary.append({
            "method": method,
            "n_modes": n_modes,
            "n_active_nodes": int(float(first["n_active_nodes"])),
            "n_sop_terms": int(float(first["n_sop_terms"])),
            "state_tensor_elements": state_elements,
            "time_total_mean_sec": statistics.mean(totals),
            "time_env_build_mean_sec": statistics.mean(envs),
            "time_apply_mean_sec": apply_mean,
            "memory_peak_mean_mb": statistics.mean(mems),
            "elements_per_apply_second": state_elements / apply_mean if apply_mean > 0 else float("nan"),
            "n_repeats": len(group),
        })
    return summary


def _fit(points, field):
    x = np.log(np.asarray([float(point["n_modes"]) for point in points]))
    y = np.log(np.asarray([float(point[field]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(summary):
    fits = []
    for method in FORMAL_METHODS:
        points = sorted(
            (row for row in summary if row["method"] == method),
            key=lambda row: row["n_modes"],
        )
        for metric in ALL_METRICS:
            field = METRIC_FIELDS[metric]
            selected = [row for row in points if float(row[field]) > 0]
            if len(selected) < 4:
                continue
            alpha, intercept, r2 = _fit(selected[-4:], field)
            fits.append({
                "method": method,
                "metric": metric,
                "fit_window": "largest_four",
                "alpha": alpha,
                "intercept_logC": intercept,
                "r2": r2,
                "n_points": 4,
                "x_min": int(selected[-4]["n_modes"]),
                "x_max": int(selected[-1]["n_modes"]),
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
        ("stage_time", "Wall time (s)", ("time_env_build_mean_sec", "time_apply_mean_sec")),
        ("memory", "Peak memory (MB)", ("memory_peak_mean_mb",)),
        ("throughput", "State elements / apply s", ("elements_per_apply_second",)),
    )
    with nature_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))
        fig.subplots_adjust(left=0.075, right=0.985, bottom=0.20, top=0.90, wspace=0.25)
        for panel_index, (ax, (name, ylabel, metrics)) in enumerate(zip(axes, panels)):
            all_x = []
            for method in FORMAL_METHODS:
                points = sorted(
                    (row for row in summary if row["method"] == method),
                    key=lambda row: row["n_modes"],
                )
                if not points:
                    continue
                x = np.asarray([float(row["n_modes"]) for row in points])
                style = METHOD_STYLES[method]
                color = style["color"]
                for metric in metrics:
                    y = np.asarray([float(row[metric]) for row in points])
                    linestyle = "-" if "time" in metric or metric == "elements_per_apply_second" else "--"
                    label = method if metric == metrics[0] else None
                    ax.plot(x, y, linestyle=linestyle, color=color, label=label, **{k: v for k, v in style.items() if k != "color"})
                all_x.extend(x.tolist())
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            if all_x:
                ax.set_xticks(sorted(set(all_x)))
                ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlabel(r"Number of modes, $N_b$")
            ax.set_ylabel(ylabel)
            label_panel(ax, chr(ord("a") + panel_index), name)
            finish_axis(ax)
        axes[0].legend(loc="upper left", frameon=False)
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def generate(rows, output_prefix, figures_dir=None):
    summary = summarize_modes(rows)
    fits = compute_fits(summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_stage_summary.csv"), summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_stage_fits.csv"), fits)
    if figures_dir is None:
        pdf_path = output_prefix.with_name(output_prefix.name + "_stage_breakdown.pdf")
    else:
        pdf_path = Path(figures_dir) / "li2024_si_stage_breakdown.pdf"
    pdf, png = plot(summary, pdf_path)
    return summary, fits, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    args = parser.parse_args()
    summary, fits, pdf, png = generate(
        read_raw(args.raw), args.output_prefix, figures_dir=args.figures_dir
    )
    print(
        f"Wrote {len(summary)} summary rows, {len(fits)} fits, "
        f"and figures {pdf} and {png}"
    )


if __name__ == "__main__":
    main()
