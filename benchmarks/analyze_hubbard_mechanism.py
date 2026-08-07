#!/usr/bin/env python3
"""Mechanism analysis for the Hubbard junction: SOP support vs TTNO compression.

For each balanced (n_lead, n_phonon) point, count the non-trivial local-operator
support of every SOP term (Jordan-Wigner Z strings make some supports grow with
n_lead) and compare the total SOP local factors with the TTNO tensor elements.
This explains why flat SOP is expensive specifically for fermionic junctions.
"""

import argparse
import csv
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.benchmark_adaptive_operator_env import build_hubbard_junction_case
from benchmarks.hubbard_balanced_manifest import (
    BALANCED_PAIRS,
    HUBBARD_PRIMITIVE_BASIS,
)
from benchmarks.nature_plot_style import (
    finish_axis,
    label_panel,
    nature_style,
    save_pdf_png,
)
from renormalizer.tn import SOPBaselineOperator, TTNO


def measure_point(n_lead, n_phonon, primitive_basis=HUBBARD_PRIMITIVE_BASIS):
    tree, terms, _psi = build_hubbard_junction_case(
        n_lead=n_lead,
        n_phonon=n_phonon,
        max_phonon_basis=primitive_basis,
        force_phonon_basis=primitive_basis,
        phonon_contract_primitive=False,
    )
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    supports = [len(term.local_ops) for term in sop.terms]
    sop_factors = sum(supports)
    ttno_elements = int(sum(node.tensor.size for node in ttno.node_list))

    phonon_leaf_modes = []
    phonon_elements = 0
    for tree_node, tensor_node in zip(tree.node_list, ttno.node_list):
        n_phonon_modes = sum(
            basis.__class__.__name__ == "BasisSHO" for basis in tree_node.basis_sets
        )
        if n_phonon_modes:
            phonon_leaf_modes.append(n_phonon_modes)
            phonon_elements += int(tensor_node.tensor.size)

    return {
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_total_sites": 4 * n_lead + 2 + n_phonon,
        "n_sop_terms": sop.n_terms,
        "support_mean": statistics.mean(supports),
        "support_max": max(supports),
        "support_histogram": json.dumps(
            {str(k): supports.count(k) for k in sorted(set(supports))},
            sort_keys=True,
        ),
        "sop_local_factors": sop_factors,
        "ttno_tensor_elements": ttno_elements,
        "phonon_leaf_modes": json.dumps(sorted(phonon_leaf_modes)),
        "n_phonon_leaf_nodes": len(phonon_leaf_modes),
        "phonon_operator_elements": phonon_elements,
        "non_phonon_operator_elements": ttno_elements - phonon_elements,
        "compression_ratio": sop_factors / ttno_elements,
        "ttno_max_bond": max(ttno.bond_dims),
        "ttno_mean_bond": float(np.mean(ttno.bond_dims)),
    }


def _fit(points, field):
    x = np.log(np.asarray([float(point["n_total_sites"]) for point in points]))
    y = np.log(np.asarray([float(point[field]) for point in points]))
    alpha, intercept = np.polyfit(x, y, 1)
    prediction = alpha * x + intercept
    residual = float(np.sum((y - prediction) ** 2))
    total = float(np.sum((y - np.mean(y)) ** 2))
    return float(alpha), float(intercept), 1.0 if total == 0 else 1.0 - residual / total


def compute_fits(summary):
    points = sorted(summary, key=lambda row: row["n_total_sites"])
    if len(points) < 4:
        return []
    fits = []
    for field in ("sop_local_factors", "ttno_tensor_elements", "support_mean", "support_max"):
        alpha, intercept, r2 = _fit(points[-4:], field)
        fits.append({
            "quantity": field,
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


def plot(summary, fits, pdf_path):
    points = sorted(summary, key=lambda row: row["n_total_sites"])
    x = np.asarray([float(row["n_total_sites"]) for row in points])
    with nature_style():
        fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
        fig.subplots_adjust(left=0.11, right=0.985, bottom=0.22, top=0.88, wspace=0.28)

        ax = axes[0]
        mean_y = np.asarray([float(row["support_mean"]) for row in points])
        max_y = np.asarray([float(row["support_max"]) for row in points])
        ax.plot(x, mean_y, marker="o", color="#00529B", label="mean support")
        ax.plot(x, max_y, marker="s", color="#CC0000", label="max support")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks(x.tolist())
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel(r"Total sites, $N$")
        ax.set_ylabel("Non-trivial local ops per SOP term")
        label_panel(ax, "a", "SOP term support")
        finish_axis(ax)
        ax.legend(loc="upper left", frameon=False)

        ax = axes[1]
        sop_y = np.asarray([float(row["sop_local_factors"]) for row in points])
        ttno_y = np.asarray([float(row["ttno_tensor_elements"]) for row in points])
        ax.plot(x, sop_y, marker="o", color="#00529B", label="SOP local factors")
        ax.plot(x, ttno_y, marker="s", color="#007A33", label="TTNO tensor elements")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks(x.tolist())
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel(r"Total sites, $N$")
        ax.set_ylabel("Total operator factors / elements")
        label_panel(ax, "b", "SOP factors vs TTNO elements")
        finish_axis(ax)
        ax.legend(loc="upper left", frameon=False)

        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png


def generate(output_prefix, figures_dir=None):
    summary = [measure_point(n_lead, n_phonon) for n_lead, n_phonon in BALANCED_PAIRS]
    fits = compute_fits(summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_mechanism_summary.csv"), summary)
    _write_csv(output_prefix.with_name(output_prefix.name + "_mechanism_fits.csv"), fits)
    if figures_dir is None:
        pdf_path = output_prefix.with_name(output_prefix.name + "_mechanism_support.pdf")
    else:
        pdf_path = Path(figures_dir) / "hubbard_mechanism_support.pdf"
    pdf, png = plot(summary, fits, pdf_path)
    return summary, fits, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    args = parser.parse_args()
    summary, fits, pdf, png = generate(args.output_prefix, args.figures_dir)
    print(
        f"Wrote {len(summary)} summary rows, {len(fits)} fits, "
        f"and figures {pdf} and {png}"
    )


if __name__ == "__main__":
    main()
