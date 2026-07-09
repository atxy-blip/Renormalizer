#!/usr/bin/env python3
"""Plot mean-per-size scaling figures for the adaptive operator benchmark."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHODS = ("sop_no_env", "sop_with_env", "ttno_with_env")
METHOD_LABELS = {
    "sop_no_env": "SOP no env",
    "sop_with_env": "SOP with env",
    "ttno_with_env": "TTNO with env",
}
METHOD_COLORS = {
    "sop_no_env": "#a23b3b",
    "sop_with_env": "#2f6f9f",
    "ttno_with_env": "#2f7d46",
}
PATH_LABELS = {
    "lead_only": "Lead-only scaling",
    "balanced_lead_phonon": "Balanced lead-phonon scaling",
}


SUMMARY_FIELDS = [
    "scaling_path",
    "n_lead",
    "n_phonon",
    "n_total_sites",
    "n_sop_terms",
    "ttno_max_bond",
    "ttno_mean_bond",
    "method",
    "n_repeats",
    "time_total_mean_sec",
    "time_total_std_sec",
    "time_env_build_mean_sec",
    "time_apply_mean_sec",
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


def summarize(rows):
    groups = defaultdict(list)
    meta = {}
    for row in rows:
        if row["status"] != "ok":
            continue
        key = (row["scaling_path"], int(row["n_lead"]), int(row["n_phonon"]), row["method"])
        groups[key].append(row)
        meta[key] = row

    summary = []
    for key in sorted(groups):
        path, n_lead, n_phonon, method = key
        group = groups[key]
        m = meta[key]
        times = [float(r["time_total_sec"]) for r in group]
        env_times = [float(r["time_env_build_sec"]) for r in group]
        apply_times = [float(r["time_apply_sec"]) for r in group]
        relerrs = [float(r["relative_error_vs_ttno"]) for r in group]
        summary.append({
            "scaling_path": path,
            "n_lead": n_lead,
            "n_phonon": n_phonon,
            "n_total_sites": int(m["n_total_sites"]),
            "n_sop_terms": int(m["n_sop_terms"]),
            "ttno_max_bond": int(float(m["ttno_max_bond"])),
            "ttno_mean_bond": float(m["ttno_mean_bond"]),
            "method": method,
            "n_repeats": len(group),
            "time_total_mean_sec": mean(times),
            "time_total_std_sec": stdev(times),
            "time_env_build_mean_sec": mean(env_times),
            "time_apply_mean_sec": mean(apply_times),
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
    x_axes = ("n_total_sites", "n_sop_terms", "n_lead", "n_phonon")
    paths = sorted({r["scaling_path"] for r in summary})
    for path in paths:
        for method in METHODS:
            points = [
                r for r in summary
                if r["scaling_path"] == path and r["method"] == method and r["time_total_mean_sec"] > 0
            ]
            points.sort(key=lambda r: (float(r["n_total_sites"]), float(r["n_sop_terms"])))
            for x_axis in x_axes:
                if x_axis == "n_phonon" and path == "lead_only":
                    continue
                valid = [p for p in points if float(p[x_axis]) > 0]
                for fit_window in ("all_mean", "large_mean"):
                    if fit_window == "large_mean" and len(valid) >= 4:
                        used = valid[len(valid) // 2:]
                    else:
                        used = valid
                    excluded = [f"{p['n_lead']}:{p['n_phonon']}" for p in valid if p not in used]
                    if len(used) < 2:
                        alpha = intercept = r2 = math.nan
                    else:
                        alpha, intercept, r2 = linfit(used, x_axis)
                    fits.append({
                        "scaling_path": path,
                        "method": method,
                        "x_axis": x_axis,
                        "fit_window": fit_window,
                        "alpha": alpha,
                        "intercept_logC": intercept,
                        "r2": r2,
                        "n_points_used": len(used),
                        "points_excluded": json.dumps(excluded),
                    })
    return fits


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fit_lookup(fits, path, method, x_axis, window="large_mean"):
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


def plot_time(summary, fits, output_prefix, x_axis):
    paths = ("lead_only", "balanced_lead_phonon")
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), sharey=False)
    for ax, path in zip(axes, paths):
        for method in METHODS:
            pts = path_method_points(summary, path, method)
            x = [float(p[x_axis]) for p in pts]
            y = [float(p["time_total_mean_sec"]) for p in pts]
            yerr = [float(p["time_total_std_sec"]) for p in pts]
            alpha = fit_lookup(fits, path, method, x_axis)["alpha"]
            ax.errorbar(
                x,
                y,
                yerr=yerr,
                marker="o",
                linewidth=1.8,
                capsize=3,
                color=METHOD_COLORS[method],
                label=f"{METHOD_LABELS[method]} (alpha={alpha:.2f})",
            )
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_title(PATH_LABELS[path])
        ax.set_xlabel(x_axis)
        ax.grid(True, which="both", alpha=0.25)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Mean wall time (s)")
    fig.tight_layout()
    fig.savefig(output_prefix.with_name(f"{output_prefix.name}_time_vs_{x_axis}.png"), dpi=240)
    fig.savefig(output_prefix.with_name(f"{output_prefix.name}_time_vs_{x_axis}.pdf"))
    plt.close(fig)


def plot_diagnostics(summary, output_prefix):
    paths = ("lead_only", "balanced_lead_phonon")
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.2))
    for row_idx, path in enumerate(paths):
        ttno_pts = path_method_points(summary, path, "ttno_with_env")
        x = [float(p["n_total_sites"]) for p in ttno_pts]
        axes[row_idx, 0].plot(x, [float(p["n_sop_terms"]) for p in ttno_pts], marker="o", color="#555555")
        axes[row_idx, 0].set_ylabel(f"{PATH_LABELS[path]}\nSOP terms")
        axes[row_idx, 1].plot(x, [float(p["ttno_max_bond"]) for p in ttno_pts], marker="o", color="#555555")
        axes[row_idx, 1].set_ylabel("TTNO max bond")

        means = {method: path_method_points(summary, path, method) for method in METHODS}
        by_size = defaultdict(dict)
        for method, pts in means.items():
            for p in pts:
                by_size[(p["n_lead"], p["n_phonon"])][method] = p
        speed_x = []
        speed_no_to_env = []
        speed_env_to_ttno = []
        speed_no_to_ttno = []
        for key in sorted(by_size, key=lambda k: float(by_size[k]["ttno_with_env"]["n_total_sites"])):
            item = by_size[key]
            speed_x.append(float(item["ttno_with_env"]["n_total_sites"]))
            no_env = float(item["sop_no_env"]["time_total_mean_sec"])
            with_env = float(item["sop_with_env"]["time_total_mean_sec"])
            ttno = float(item["ttno_with_env"]["time_total_mean_sec"])
            speed_no_to_env.append(no_env / with_env)
            speed_env_to_ttno.append(with_env / ttno)
            speed_no_to_ttno.append(no_env / ttno)
        axes[row_idx, 2].plot(speed_x, speed_no_to_env, marker="o", label="no env / with env", color=METHOD_COLORS["sop_no_env"])
        axes[row_idx, 2].plot(speed_x, speed_env_to_ttno, marker="s", label="with env / TTNO", color=METHOD_COLORS["sop_with_env"])
        axes[row_idx, 2].plot(speed_x, speed_no_to_ttno, marker="^", label="no env / TTNO", color=METHOD_COLORS["ttno_with_env"])
        axes[row_idx, 2].set_ylabel("Speedup")
        axes[row_idx, 2].set_yscale("log")
        axes[row_idx, 2].legend(fontsize=8)

        for col in range(3):
            axes[row_idx, col].set_xscale("log", base=2)
            axes[row_idx, col].set_xlabel("n_total_sites")
            axes[row_idx, col].grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_prefix.with_name(f"{output_prefix.name}_diagnostics.png"), dpi=240)
    fig.savefig(output_prefix.with_name(f"{output_prefix.name}_diagnostics.pdf"))
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()

    rows = read_raw(args.raw)
    summary = summarize(rows)
    fits = compute_fits(summary)
    write_csv(args.output_prefix.with_name(f"{args.output_prefix.name}_summary.csv"), summary, SUMMARY_FIELDS)
    write_csv(args.output_prefix.with_name(f"{args.output_prefix.name}_mean_fits.csv"), fits, FIT_FIELDS)
    plot_time(summary, fits, args.output_prefix, "n_total_sites")
    plot_time(summary, fits, args.output_prefix, "n_sop_terms")
    plot_diagnostics(summary, args.output_prefix)

    print(f"Wrote {args.output_prefix.with_name(args.output_prefix.name + '_summary.csv')}")
    print(f"Wrote {args.output_prefix.with_name(args.output_prefix.name + '_mean_fits.csv')}")


if __name__ == "__main__":
    main()
