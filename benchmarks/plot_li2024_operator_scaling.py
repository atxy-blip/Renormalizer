#!/usr/bin/env python3
"""Plot the Li.W.2024 spin--boson setup for the three operator kernels."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.li2024_formal_manifest import FORMAL_METHODS


METHOD_LABELS = {
    "sop_no_env": "SOP no env",
    "sop_mctdh_like_state_env": "SOP strict state env",
    "ttno_with_env": "TTNO with env",
}
METHOD_COLORS = {
    "sop_no_env": "#a23b3b",
    "sop_mctdh_like_state_env": "#a06a16",
    "ttno_with_env": "#2f7d46",
}
REFERENCE_POWERS = {
    "modes": {
        "sop_no_env": 3.0,
        "sop_mctdh_like_state_env": 2.0,
        "ttno_with_env": 1.0,
    },
    "state_bond": {method: 4.0 for method in FORMAL_METHODS},
    "primitive_basis": {method: 0.0 for method in FORMAL_METHODS},
}


@dataclass(frozen=True)
class Panel:
    name: str
    x_field: str
    xlabel: str
    title: str
    symbol: str


PANELS = (
    Panel("modes", "n_modes", r"Number of modes, $N_b$", r"Mode number $N_b$", "N_b"),
    Panel("state_bond", "target_state_bond", r"State bond dimension, $M_s$", r"State bond $M_s$", "M_s"),
    Panel("primitive_basis", "primitive_basis_dim", r"Primitive basis, $d$", r"Primitive basis $d$", "d"),
)


def read_raw(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def _as_bool(value):
    return value if isinstance(value, bool) else str(value).lower() == "true"


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok" or row.get("method") not in FORMAL_METHODS:
            continue
        key = (
            row["panel"],
            row["method"],
            int(row["n_modes"]),
            int(row["target_state_bond"]),
            int(row["primitive_basis_dim"]),
            _as_bool(row["contract_primitive"]),
        )
        groups[key].append(row)

    summary = []
    for key in sorted(groups):
        panel, method, n_modes, state_bond, primitive_basis, contract_primitive = key
        group = groups[key]
        total = [float(row["time_total_sec"]) for row in group]
        env = [float(row["time_env_build_sec"]) for row in group]
        apply = [float(row["time_apply_sec"]) for row in group]
        errors = [float(row["relative_error_vs_ttno"]) for row in group]
        first = group[0]
        summary.append({
            "panel": panel,
            "method": method,
            "n_modes": n_modes,
            "target_state_bond": state_bond,
            "state_max_bond": int(float(first["state_max_bond"])),
            "primitive_basis_dim": primitive_basis,
            "contract_primitive": contract_primitive,
            "phonon_tree_layout": first["phonon_tree_layout"],
            "n_active_nodes": int(float(first["n_active_nodes"])),
            "n_sop_terms": int(float(first["n_sop_terms"])),
            "ttno_max_bond": int(float(first["ttno_max_bond"])),
            "state_tensor_elements": int(float(first["state_tensor_elements"])),
            "operator_tensor_elements": int(float(first["operator_tensor_elements"])),
            "n_repeats": len(group),
            "time_total_mean_sec": statistics.mean(total),
            "time_total_std_sec": statistics.stdev(total) if len(total) > 1 else 0.0,
            "time_env_build_mean_sec": statistics.mean(env),
            "time_apply_mean_sec": statistics.mean(apply),
            "relative_error_max_vs_ttno": max(errors),
        })
    return summary


def _fit(points, x_field):
    x = np.log(np.asarray([float(point[x_field]) for point in points]))
    y = np.log(np.asarray([float(point["time_total_mean_sec"]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(summary):
    fits = []
    for panel in PANELS:
        for method in FORMAL_METHODS:
            points = sorted(
                (
                    row for row in summary
                    if row["panel"] == panel.name
                    and row["method"] == method
                    and float(row["time_total_mean_sec"]) > 0
                ),
                key=lambda row: float(row[panel.x_field]),
            )
            for window, selected in (("all", points), ("largest_four", points[-4:])):
                if len(selected) < 2:
                    continue
                alpha, intercept, r2 = _fit(selected, panel.x_field)
                fits.append({
                    "panel": panel.name,
                    "method": method,
                    "x_axis": panel.x_field,
                    "fit_window": window,
                    "alpha": alpha,
                    "intercept_logC": intercept,
                    "r2": r2,
                    "n_points": len(selected),
                    "x_min": float(selected[0][panel.x_field]),
                    "x_max": float(selected[-1][panel.x_field]),
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
        writer.writerows(rows)


def _guide_label(symbol, power):
    if power == 0:
        return r"$\propto \mathrm{const}$"
    return rf"$\propto {symbol}^{int(power)}$"


def plot(summary, output_prefix):
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), sharey=True)
    for ax, panel in zip(axes, PANELS):
        all_x = []
        for method in FORMAL_METHODS:
            points = sorted(
                (
                    row for row in summary
                    if row["panel"] == panel.name and row["method"] == method
                ),
                key=lambda row: float(row[panel.x_field]),
            )
            if not points:
                continue
            x = np.asarray([float(row[panel.x_field]) for row in points])
            y = np.asarray([float(row["time_total_mean_sec"]) for row in points])
            yerr = np.asarray([float(row["time_total_std_sec"]) for row in points])
            color = METHOD_COLORS[method]
            ax.errorbar(
                x,
                y,
                yerr=yerr,
                marker="o",
                markersize=5,
                linewidth=1.4,
                capsize=2,
                color=color,
                label=METHOD_LABELS[method],
            )

            power = REFERENCE_POWERS[panel.name][method]
            ref_x = x if panel.name == "modes" else x[len(x) // 2 :]
            ref_y = y[-1] * (ref_x / ref_x[-1]) ** power
            ax.plot(ref_x, ref_y, linestyle="--", linewidth=1.2, color=color, alpha=0.7)
            ax.annotate(
                _guide_label(panel.symbol, power),
                xy=(ref_x[-1], ref_y[-1]),
                xytext=(3, 0),
                textcoords="offset points",
                color=color,
                fontsize=8,
                va="center",
            )
            all_x.extend(x.tolist())

        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        if all_x:
            ax.set_xticks(sorted(set(all_x)))
            ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel(panel.xlabel)
        ax.set_title(panel.title)
        ax.grid(True, which="both", linewidth=0.55, alpha=0.25)

    axes[0].set_ylabel("All-node local-action wall time (s)")
    axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9)
    fig.suptitle("Li.W.2024 spin--boson setup: operator-kernel scaling", y=1.04)
    fig.tight_layout()
    output = output_prefix.with_name(output_prefix.name + "_scaling_three_panel.pdf")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


def generate(rows, output_prefix):
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = {row.get("case_name") for row in ok_rows}
    quantities = {row.get("quantity") for row in ok_rows}
    if cases != {"li2024_spin_boson"}:
        raise ValueError(f"expected only li2024_spin_boson rows, found {sorted(cases)}")
    if quantities != {"local_effective_1site_apply_all_nodes"}:
        raise ValueError(f"expected all-node local actions, found {sorted(quantities)}")
    summary = summarize(rows)
    fits = compute_fits(summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_summary.csv"), summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_fits.csv"), fits)
    pdf = plot(summary, output_prefix)
    return summary, fits, pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    summary, fits, pdf = generate(read_raw(args.raw), args.output_prefix)
    print(f"Wrote {len(summary)} summary rows, {len(fits)} fits, and {pdf}")


if __name__ == "__main__":
    main()
