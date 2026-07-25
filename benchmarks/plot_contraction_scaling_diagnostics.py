#!/usr/bin/env python3
"""Plot mathematical and measured contraction-scaling diagnostics."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.nature_plot_style import (
    finish_axis,
    label_panel,
    nature_style,
    save_pdf_png,
)


INTEGER_FIELDS = {
    "state_bond",
    "primitive_basis",
    "operator_bond",
    "n_repeats",
}
BOOLEAN_FIELDS = {"contract_primitive"}
FIT_FIELDS = (
    "figure",
    "panel",
    "kernel",
    "metric",
    "x_axis",
    "fit_window",
    "alpha",
    "intercept_logC",
    "r2",
    "n_points",
    "x_min",
    "x_max",
)

COLORS = {
    "sop": "#00529B",
    "ttno": "#007A33",
    "paired": "#CC0000",
    "contracted": "#007A33",
    "operator": "#d17a22",
    "environment": "#3575a8",
    "apply": "#7655a8",
    "state": "#6b7280",
}


def read_summary(path):
    rows = []
    with Path(path).open(newline="") as f:
        for raw in csv.DictReader(f):
            row = {}
            for field, value in raw.items():
                if value == "":
                    continue
                if field in INTEGER_FIELDS:
                    row[field] = int(float(value))
                elif field in BOOLEAN_FIELDS:
                    row[field] = value.lower() == "true"
                elif field in ("panel", "kernel"):
                    row[field] = value
                else:
                    row[field] = float(value)
            rows.append(row)
    return rows


def select_series(rows, panel, kernel, x_field):
    return sorted(
        (row for row in rows if row["panel"] == panel and row["kernel"] == kernel),
        key=lambda row: float(row[x_field]),
    )


def log_fit(rows, x_field, y_field, tail=None):
    points = sorted({
        (float(row[x_field]), float(row[y_field]))
        for row in rows
        if x_field in row and y_field in row
        and float(row[x_field]) > 0 and float(row[y_field]) > 0
    })
    if tail is not None:
        points = points[-int(tail):]
    if len(points) < 2:
        raise ValueError(f"need at least two positive points for {x_field}/{y_field}")

    logx = np.log(np.asarray([point[0] for point in points], dtype=float))
    logy = np.log(np.asarray([point[1] for point in points], dtype=float))
    alpha, intercept = np.polyfit(logx, logy, 1)
    predicted = alpha * logx + intercept
    residual = float(np.sum((logy - predicted) ** 2))
    total = float(np.sum((logy - np.mean(logy)) ** 2))
    r2 = 1.0 if total == 0 else 1.0 - residual / total
    return {
        "alpha": float(alpha),
        "intercept_logC": float(intercept),
        "r2": r2,
        "n_points": len(points),
        "x_min": points[0][0],
        "x_max": points[-1][0],
    }


def _record_fits(records, figure, panel, kernel, metric, x_field, rows):
    y_field = f"{metric}_median"
    for window, tail in (("all", None), ("largest_four", 4)):
        fit = log_fit(rows, x_field, y_field, tail=tail)
        records.append({
            "figure": figure,
            "panel": panel,
            "kernel": kernel,
            "metric": metric,
            "x_axis": x_field,
            "fit_window": window,
            **fit,
        })
    return records[-1]


def _plot_metric(
    ax,
    records,
    figure,
    panel,
    kernel,
    rows,
    x_field,
    metric,
    label,
    color,
    marker,
    linestyle="-",
):
    y_field = f"{metric}_median"
    std_field = f"{metric}_std"
    x = np.asarray([float(row[x_field]) for row in rows])
    y = np.asarray([float(row[y_field]) for row in rows])
    std = np.asarray([float(row.get(std_field, 0.0)) for row in rows])
    tail_fit = _record_fits(records, figure, panel, kernel, metric, x_field, rows)
    plotted_label = label + rf" ($\alpha_{{tail}}={tail_fit['alpha']:.2f}$)"
    ax.plot(
        x,
        y,
        color=color,
        marker=marker,
        linestyle=linestyle,
        label=plotted_label,
    )
    if np.any(std > 0):
        lower = np.maximum(y - std, y * 1e-6)
        ax.fill_between(x, lower, y + std, color=color, alpha=0.13, linewidth=0)
    return x, y


def _reference_line(ax, x, y, power, label, color="#555555", position=0.92):
    count = min(4, len(x))
    ref_x = np.asarray(x[-count:], dtype=float)
    ref_y = float(y[-1]) * (ref_x / ref_x[-1]) ** power
    ax.plot(ref_x, ref_y, color=color, linestyle="--", alpha=0.75)
    index = 0 if count < 3 else 1
    ax.annotate(
        label,
        xy=(ref_x[index], ref_y[index]),
        xytext=(0, 4 if position >= 1 else -11),
        textcoords="offset points",
        color=color,
        fontsize=8,
        ha="center",
    )


def _finish_axis(ax, xlabel, ylabel, panel_label, title):
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    label_panel(ax, panel_label, title)
    finish_axis(ax)
    ax.legend(
        loc="upper left",
        frameon=False,
        handlelength=1.6,
        handletextpad=0.5,
        labelspacing=0.3,
        borderaxespad=0.4,
    )


def _plot_complexity_validation(rows, records, output_dir):
    figure_name = "complexity_validation"
    with nature_style():
        fig, axes = plt.subplots(2, 2, figsize=(7.0, 5.4))
        fig.subplots_adjust(
            left=0.11,
            right=0.985,
            bottom=0.10,
            top=0.96,
            wspace=0.28,
            hspace=0.34,
        )

        internal = (
            ("sop_internal", "SOP internal", COLORS["sop"], "o"),
            ("ttno_internal", "TTNO internal", COLORS["ttno"], "s"),
        )
        internal_values = {}
        for kernel, label, color, marker in internal:
            series = select_series(rows, "internal_ms", kernel, "state_bond")
            internal_values[kernel] = _plot_metric(
                axes[0, 0], records, figure_name, "internal_ms", kernel,
                series, "state_bond", "optimized_flops", label, color, marker,
            )
            _plot_metric(
                axes[0, 1], records, figure_name, "internal_ms", kernel,
                series, "state_bond", "apply_sec", label, color, marker,
            )
        _reference_line(
            axes[0, 0], *internal_values["sop_internal"], 4,
            r"$M_s^4$", color=COLORS["sop"],
        )
        _finish_axis(
            axes[0, 0], r"State bond dimension $M_s$", "Optimized FLOPs",
            "a", "Internal-node mathematical cost",
        )
        _finish_axis(
            axes[0, 1], r"State bond dimension $M_s$",
            "Dense-kernel apply time (s)", "b", "Internal-node wall time",
        )

        leaves = (
            (
                "ttno_leaf_paired",
                "Paired leaf",
                COLORS["paired"],
                "o",
                4,
                r"$d^4$",
            ),
            (
                "ttno_leaf_contracted",
                "Contracted leaf",
                COLORS["contracted"],
                "s",
                2,
                r"$d^2$",
            ),
        )
        for kernel, label, color, marker, power, guide in leaves:
            series = select_series(rows, "leaf_d", kernel, "primitive_basis")
            x, y = _plot_metric(
                axes[1, 0], records, figure_name, "leaf_d", kernel,
                series, "primitive_basis", "optimized_flops", label, color,
                marker,
            )
            _reference_line(axes[1, 0], x, y, power, guide, color=color)
            _plot_metric(
                axes[1, 1], records, figure_name, "leaf_d", kernel,
                series, "primitive_basis", "apply_sec", label, color, marker,
            )
        _finish_axis(
            axes[1, 0], r"Primitive basis dimension $d$", "Optimized FLOPs",
            "c", "Leaf mathematical cost",
        )
        _finish_axis(
            axes[1, 1], r"Primitive basis dimension $d$",
            "Dense-kernel apply time (s)", "d", "Leaf wall time",
        )

        pdf, png = save_pdf_png(fig, output_dir / f"{figure_name}.pdf")
        plt.close(fig)
    return pdf, png


def _plot_model_mechanism(rows, records, output_dir):
    figure_name = "model_mechanism"
    with nature_style():
        fig, axes = plt.subplots(2, 2, figsize=(7.0, 5.4))
        fig.subplots_adjust(
            left=0.11,
            right=0.985,
            bottom=0.10,
            top=0.96,
            wspace=0.28,
            hspace=0.34,
        )

        models = (
            ("ttno_model_paired", "Paired tree", COLORS["paired"], "o"),
            (
                "ttno_model_contracted",
                "Contracted tree",
                COLORS["contracted"],
                "s",
            ),
        )

        model_rows = {}
        for kernel, label, color, marker in models:
            series = select_series(rows, "model_d", kernel, "primitive_basis")
            model_rows[kernel] = series
            _plot_metric(
                axes[0, 0], records, figure_name, "model_d", kernel,
                series, "primitive_basis", "time_total_sec", label, color,
                marker,
            )
        _finish_axis(
            axes[0, 0], r"Primitive basis dimension $d$",
            "Measured workflow time (s)", "a", "Full-model total time",
        )

        paired = model_rows["ttno_model_paired"]
        for metric, label, color, marker in (
            (
                "operator_build_sec",
                "TTNO construction",
                COLORS["operator"],
                "o",
            ),
            (
                "environment_build_sec",
                "Environment construction",
                COLORS["environment"],
                "s",
            ),
            ("apply_sec", "Local actions", COLORS["apply"], "^"),
        ):
            _plot_metric(
                axes[0, 1], records, figure_name, "model_d",
                "ttno_model_paired", paired, "primitive_basis", metric, label,
                color, marker,
            )
        _finish_axis(
            axes[0, 1], r"Primitive basis dimension $d$", "Measured time (s)",
            "b", "Paired-tree time decomposition",
        )

        for kernel, label, color, marker in models:
            series = model_rows[kernel]
            storage_label = label.removesuffix(" tree")
            _plot_metric(
                axes[1, 0], records, figure_name, "model_d", kernel,
                series, "primitive_basis", "operator_tensor_elements",
                f"{storage_label} TTNO", color, marker,
            )
            _plot_metric(
                axes[1, 0], records, figure_name, "model_d", kernel,
                series, "primitive_basis", "state_tensor_elements",
                f"{storage_label} TTNS", color, marker, linestyle=":",
            )
            _plot_metric(
                axes[1, 1], records, figure_name, "model_d", kernel,
                series, "primitive_basis", "peak_memory_mb", label, color,
                marker,
            )
        _finish_axis(
            axes[1, 0], r"Primitive basis dimension $d$",
            "Stored tensor elements", "c", "State and operator storage",
        )
        _finish_axis(
            axes[1, 1], r"Primitive basis dimension $d$",
            "Peak resident memory (MB)", "d", "Process memory",
        )

        pdf, png = save_pdf_png(fig, output_dir / f"{figure_name}.pdf")
        plt.close(fig)
    return pdf, png


def _write_fits(path, records):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIT_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def generate_figures(summary_path, output_dir):
    rows = read_summary(summary_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    complexity_outputs = _plot_complexity_validation(rows, records, output_dir)
    model_outputs = _plot_model_mechanism(rows, records, output_dir)
    fits = output_dir / "plot_fits.csv"
    _write_fits(fits, records)
    return (*complexity_outputs, *model_outputs, fits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = generate_figures(args.summary, args.output_dir)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
