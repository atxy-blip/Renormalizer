#!/usr/bin/env python3
"""Plot the strict all-node SOP/TTNO scaling comparison."""

import argparse
import csv
import json
import math
import statistics
from dataclasses import dataclass
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


PUBLICATION_METHODS = (
    "sop_no_env",
    "sop_mctdh_like_state_env",
    "ttno_with_env",
)
REFERENCE_ALPHA = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}
METHOD_LABELS = {
    "sop_no_env": "SOP no env",
    "sop_mctdh_like_state_env": "SOP strict state env",
    "ttno_with_env": "TTNO with env",
}
METHOD_COLORS = {
    method: METHOD_STYLES[method]["color"]
    for method in PUBLICATION_METHODS
}
LEGEND_KWARGS = {
    "loc": "upper left",
    "fontsize": 8,
    "frameon": True,
    "framealpha": 0.9,
}


@dataclass(frozen=True)
class ScalingPanel:
    name: str
    x_axis: str
    xlabel: str
    symbol: str
    title: str
    preferred_paths: tuple
    reference_alpha_by_method: tuple


SCALING_PANELS = (
    ScalingPanel(
        name="site_number",
        x_axis="n_total_sites",
        xlabel=r"Number of sites, $N_{\mathrm{site}}$",
        symbol="N",
        title=r"Site number $N$",
        preferred_paths=("site_number", "lead_only", "balanced_lead_phonon"),
        reference_alpha_by_method=tuple(REFERENCE_ALPHA.items()),
    ),
    ScalingPanel(
        name="state_bond",
        x_axis="state_max_bond",
        xlabel=r"State bond dimension, $M_s$",
        symbol="M_s",
        title=r"State bond $M_s$",
        preferred_paths=("state_bond", "bond_dimension", "ms_scaling"),
        reference_alpha_by_method=tuple((method, 3.0) for method in PUBLICATION_METHODS),
    ),
    ScalingPanel(
        name="primitive_basis",
        x_axis="primitive_basis_dim",
        xlabel=r"Primitive basis dimension, $d$",
        symbol="d",
        title=r"Primitive basis $d$",
        preferred_paths=("primitive_basis", "primitive_basis_dim", "d_scaling"),
        reference_alpha_by_method=(
            ("sop_no_env", 0.0),
            ("sop_mctdh_like_state_env", 0.0),
            ("ttno_with_env", 4.0),
        ),
    ),
)


SUMMARY_FIELDS = [
    "scaling_path",
    "n_lead",
    "n_phonon",
    "n_total_sites",
    "n_sop_terms",
    "n_active_nodes",
    "tree_depth",
    "n_sop_terms_times_n_total_sites",
    "n_sop_terms_times_n_active_nodes",
    "n_sop_terms_times_tree_depth",
    "ttno_max_bond",
    "ttno_mean_bond",
    "state_max_bond",
    "primitive_basis_dim",
    "method",
    "n_repeats",
    "time_total_mean_sec",
    "time_total_std_sec",
    "time_env_build_mean_sec",
    "time_term_loop_mean_sec",
    "time_apply_mean_sec",
    "n_env_cache_entries_mean",
    "relative_error_max_vs_ttno",
]

FIT_FIELDS = [
    "scaling_path",
    "method",
    "x_axis",
    "fit_window",
    "alpha",
    "intercept_logC",
    "r2",
    "n_points_used",
    "points_excluded",
]


def read_raw(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def mean(values):
    return statistics.mean(values)


def stdev(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def primitive_basis_dim(row):
    try:
        basis_summary = json.loads(row.get("local_basis_summary", "{}"))
    except json.JSONDecodeError:
        return math.nan
    dims = []
    for key in basis_summary:
        try:
            dims.append(float(key.rsplit(":", 1)[1]))
        except (IndexError, ValueError):
            continue
    return max(dims) if dims else math.nan


def summarize(rows):
    groups = defaultdict(list)
    meta = {}
    for row in rows:
        if row["status"] != "ok" or row["method"] not in PUBLICATION_METHODS:
            continue
        key = (
            row["scaling_path"],
            int(row["n_lead"]),
            int(row["n_phonon"]),
            int(float(row.get("state_max_bond", 0))),
            primitive_basis_dim(row),
            row["method"],
        )
        groups[key].append(row)
        meta[key] = row

    summary = []
    for key in sorted(groups):
        path, n_lead, n_phonon, _state_max_bond, _primitive_basis_dim, method = key
        group = groups[key]
        m = meta[key]
        times = [float(r["time_total_sec"]) for r in group]
        env_times = [float(r["time_env_build_sec"]) for r in group]
        term_loop_times = [float(r.get("time_term_loop_sec", 0.0)) for r in group]
        apply_times = [float(r["time_apply_sec"]) for r in group]
        env_cache_entries = [float(r.get("n_env_cache_entries", 0.0)) for r in group]
        relerrs = [float(r["relative_error_vs_ttno"]) for r in group]
        n_active_nodes = int(float(m.get("n_active_nodes", 1)))
        tree_depth = int(float(m.get("tree_depth", 0)))
        summary.append({
            "scaling_path": path,
            "n_lead": n_lead,
            "n_phonon": n_phonon,
            "n_total_sites": int(m["n_total_sites"]),
            "n_sop_terms": int(m["n_sop_terms"]),
            "n_active_nodes": n_active_nodes,
            "tree_depth": tree_depth,
            "n_sop_terms_times_n_total_sites": int(float(m.get(
                "n_sop_terms_times_n_total_sites",
                float(m["n_sop_terms"]) * float(m["n_total_sites"]),
            ))),
            "n_sop_terms_times_n_active_nodes": int(float(m.get(
                "n_sop_terms_times_n_active_nodes",
                float(m["n_sop_terms"]) * n_active_nodes,
            ))),
            "n_sop_terms_times_tree_depth": int(float(m.get(
                "n_sop_terms_times_tree_depth",
                float(m["n_sop_terms"]) * tree_depth,
            ))),
            "ttno_max_bond": int(float(m["ttno_max_bond"])),
            "ttno_mean_bond": float(m["ttno_mean_bond"]),
            "state_max_bond": int(float(m.get("state_max_bond", 0))),
            "primitive_basis_dim": primitive_basis_dim(m),
            "method": method,
            "n_repeats": len(group),
            "time_total_mean_sec": mean(times),
            "time_total_std_sec": stdev(times),
            "time_env_build_mean_sec": mean(env_times),
            "time_term_loop_mean_sec": mean(term_loop_times),
            "time_apply_mean_sec": mean(apply_times),
            "n_env_cache_entries_mean": mean(env_cache_entries),
            "relative_error_max_vs_ttno": max(relerrs),
        })
    return summary


def linfit(points, x_axis):
    x = np.log(np.array([float(p[x_axis]) for p in points]))
    y = np.log(np.array([float(p["time_total_mean_sec"]) for p in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    pred = alpha * x + intercept
    ss_res = float(np.sum((y - pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 if ss_tot == 0 else 1.0 - ss_res / ss_tot
    return float(alpha), float(intercept), r2


def compute_fits(summary):
    fits = []
    paths = sorted({r["scaling_path"] for r in summary})
    for path in paths:
        for method in PUBLICATION_METHODS:
            for panel in SCALING_PANELS:
                points = [
                    r for r in summary
                    if r["scaling_path"] == path and r["method"] == method and r["time_total_mean_sec"] > 0
                ]
                points.sort(key=lambda r: (float(r[panel.x_axis]), float(r["n_total_sites"])))
                valid = [p for p in points if float(p[panel.x_axis]) > 0]
                distinct_x = {float(p[panel.x_axis]) for p in valid}
                if len(valid) < 2 or len(distinct_x) < 2:
                    alpha = intercept = r2 = math.nan
                else:
                    alpha, intercept, r2 = linfit(valid, panel.x_axis)
                fits.append({
                    "scaling_path": path,
                    "method": method,
                    "x_axis": panel.x_axis,
                    "fit_window": "all_mean",
                    "alpha": alpha,
                    "intercept_logC": intercept,
                    "r2": r2,
                    "n_points_used": len(valid),
                    "points_excluded": json.dumps([]),
                })
    return fits


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fit_lookup(fits, path, method, x_axis="n_total_sites", window="all_mean"):
    for fit in fits:
        if (
            fit["scaling_path"] == path
            and fit["method"] == method
            and fit["x_axis"] == x_axis
            and fit["fit_window"] == window
        ):
            return fit
    raise KeyError((path, method, x_axis, window))


def path_method_points(summary, path, method):
    pts = [r for r in summary if r["scaling_path"] == path and r["method"] == method]
    pts.sort(key=lambda r: float(r["n_total_sites"]))
    return pts


def panel_path(summary, panel):
    paths = sorted({row["scaling_path"] for row in summary})
    for preferred in panel.preferred_paths:
        if preferred in paths and _path_has_varying_axis(summary, preferred, panel.x_axis):
            return preferred
    for path in paths:
        if _path_has_varying_axis(summary, path, panel.x_axis):
            return path
    return None


def _path_has_varying_axis(summary, path, x_axis):
    values = {
        float(row[x_axis])
        for row in summary
        if row["scaling_path"] == path
        and row["method"] in PUBLICATION_METHODS
        and float(row.get("time_total_mean_sec", 0.0)) > 0
        and float(row.get(x_axis, 0.0)) > 0
    }
    return len(values) >= 2


def reference_curve(x, y, alpha):
    """Return a reference power law centered on a measured data series."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_anchor = float(np.exp(np.mean(np.log(x))))
    y_anchor = float(np.exp(np.mean(np.log(y))))
    return x, y_anchor * (x / x_anchor) ** alpha


def reference_curve_last_half(x, y, alpha):
    """Return a power-law guide over the latter half, ending at the last point."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x_ref = x[len(x) // 2 :]
    return x_ref, y[-1] * (x_ref / x[-1]) ** alpha


def method_legend_label(method):
    return METHOD_LABELS[method]


def reference_annotation(symbol, alpha):
    if alpha == 0:
        return r"$\propto \mathrm{const}$"
    return rf"$\propto {symbol}^{int(alpha)}$"


def validate_publication_input(rows):
    quantities = {row["quantity"] for row in rows if row["status"] == "ok"}
    expected_quantity = {"local_effective_1site_apply_all_nodes"}
    if quantities != expected_quantity:
        raise ValueError(
            "publication plot requires all-node local actions; "
            f"found quantities {sorted(quantities)}"
        )
    methods = {row["method"] for row in rows if row["status"] == "ok"}
    missing = set(PUBLICATION_METHODS) - methods
    if missing:
        raise ValueError(f"publication plot is missing methods: {sorted(missing)}")


def plot_publication_time(summary, fits, output_prefix):
    panel_titles = ("Site number", "State bond", "Primitive basis")
    with nature_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8), sharey=True)
        fig.subplots_adjust(
            left=0.075,
            right=0.985,
            bottom=0.20,
            top=0.90,
            wspace=0.10,
        )
        legend_handles = []
        legend_labels = []
        for panel_index, (ax, panel, panel_title) in enumerate(
            zip(axes, SCALING_PANELS, panel_titles)
        ):
            path = panel_path(summary, panel)
            reference_alpha = dict(panel.reference_alpha_by_method)
            if path is None:
                ax.text(
                    0.5,
                    0.5,
                    "not measured",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                )
                ax.set_xlabel(panel.xlabel)
                label_panel(ax, chr(ord("a") + panel_index), panel_title)
                finish_axis(ax)
                continue

            all_x = []
            for method in PUBLICATION_METHODS:
                pts = [
                    r for r in path_method_points(summary, path, method)
                    if float(r[panel.x_axis]) > 0
                    and float(r["time_total_mean_sec"]) > 0
                ]
                pts.sort(key=lambda r: float(r[panel.x_axis]))
                if len(pts) < 2:
                    continue
                x = np.asarray([float(p[panel.x_axis]) for p in pts])
                y = np.asarray([float(p["time_total_mean_sec"]) for p in pts])
                style = METHOD_STYLES[method]
                color = style["color"]
                label = method_legend_label(method)
                marker_handle, = ax.plot(
                    x,
                    y,
                    linestyle="none",
                    label=label,
                    **style,
                )
                if panel is SCALING_PANELS[0]:
                    legend_handles.append(marker_handle)
                    legend_labels.append(label)

                if method in reference_alpha:
                    if panel is SCALING_PANELS[0]:
                        x_ref, y_ref = reference_curve(
                            x,
                            y,
                            reference_alpha[method],
                        )
                    else:
                        x_ref, y_ref = reference_curve_last_half(
                            x,
                            y,
                            reference_alpha[method],
                        )
                    ax.plot(
                        x_ref,
                        y_ref,
                        linestyle="--",
                        color=color,
                        alpha=0.75,
                    )
                    ax.text(
                        0.97,
                        y_ref[-1],
                        reference_annotation(
                            panel.symbol,
                            reference_alpha[method],
                        ),
                        transform=ax.get_yaxis_transform(),
                        color=color,
                        ha="right",
                        va="center",
                        clip_on=True,
                    )
                all_x.extend(x)

            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            if all_x:
                ax.set_xticks(sorted(set(all_x)))
                ax.get_xaxis().set_major_formatter(
                    matplotlib.ticker.ScalarFormatter()
                )
            ax.set_xlabel(panel.xlabel)
            label_panel(ax, chr(ord("a") + panel_index), panel_title)
            finish_axis(ax)

        axes[0].set_ylabel("Total wall time (s)")
        if legend_handles:
            axes[0].legend(legend_handles, legend_labels, **LEGEND_KWARGS)
        pdf_path = output_prefix.with_name(
            f"{output_prefix.name}_scaling_three_panel.pdf"
        )
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    rows = read_raw(args.raw)
    validate_publication_input(rows)
    summary = summarize(rows)
    fits = compute_fits(summary)
    write_csv(args.output_prefix.with_name(f"{args.output_prefix.name}_summary.csv"), summary, SUMMARY_FIELDS)
    write_csv(args.output_prefix.with_name(f"{args.output_prefix.name}_fits.csv"), fits, FIT_FIELDS)
    pdf, png = plot_publication_time(summary, fits, args.output_prefix)

    print(f"Wrote {args.output_prefix.with_name(args.output_prefix.name + '_summary.csv')}")
    print(f"Wrote {args.output_prefix.with_name(args.output_prefix.name + '_fits.csv')}")
    print(f"Wrote {pdf}")
    print(f"Wrote {png}")


if __name__ == "__main__":
    main()
