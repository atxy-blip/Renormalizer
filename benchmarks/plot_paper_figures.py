#!/usr/bin/env python3
"""Regenerate publication-facing figures in the ../ttns-test Nature style.

Decision (JCTC methods paper):
- main text: one two-panel figure with (a) operator-structure mechanism and
  (b) per-sweep efficiency of the molecular-junction operator action.
  Numerical equivalence is stated in one sentence, not plotted (errors are
  all within machine precision; a log-scale curve would exaggerate growth).
- SI: spin-boson full-exponent scaling, stage breakdown, construction cost,
  Jordan-Wigner mechanism, cost metrics (time / memory / memory x time /
  speedup), and the full three-method Hubbard scaling.
"""

import argparse
import csv
import math
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


TTNSTEST_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.top": True,
    "ytick.right": True,
    "legend.frameon": False,
    "lines.linewidth": 1.2,
    "lines.markersize": 4.5,
    "xtick.major.pad": 3.0,
    "ytick.major.pad": 3.0,
    "axes.labelpad": 4.0,
    "figure.subplot.left": 0.15,
    "figure.subplot.right": 0.96,
    "figure.subplot.bottom": 0.15,
    "figure.subplot.top": 0.96,
}

METHODS = ("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")
METHOD_LABELS = {
    "sop_no_env": "SOP no env",
    "sop_mctdh_like_state_env": "SOP strict state env",
    "ttno_with_env": "TTNO with env",
}
METHOD_COLORS = {
    "sop_no_env": "#00529B",
    "sop_mctdh_like_state_env": "#CC0000",
    "ttno_with_env": "#007A33",
}
METHOD_MARKERS = {
    "sop_no_env": "o",
    "sop_mctdh_like_state_env": "o",
    "ttno_with_env": "s",
}
REFERENCE_POWERS = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}


def ttns_style():
    return matplotlib.rc_context(TTNSTEST_RCPARAMS)


def save_pdf_png(fig, pdf_path):
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    png_path = pdf_path.with_suffix(".png")
    fig.savefig(pdf_path, format="pdf", transparent=True)
    fig.savefig(png_path, format="png", dpi=300, transparent=True)
    return pdf_path, png_path


def read_csv(path):
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def fit_alpha(points, x_field, y_field):
    x = np.log(np.asarray([float(p[x_field]) for p in points]))
    y = np.log(np.asarray([float(p[y_field]) for p in points]))
    alpha, _ = np.polyfit(x, y, 1)
    return float(alpha)


def finish_axis(ax):
    ax.tick_params(which="major", direction="in", length=4, width=0.8, top=True, right=True)
    ax.tick_params(which="minor", direction="in", length=2, width=0.6, top=True, right=True)
    ax.minorticks_on()


def label_panel(ax, label, title):
    ax.set_title(f"({label}) {title}", loc="left")


def sort_rows(rows, x_field):
    return sorted(rows, key=lambda r: float(r[x_field]))


def plot_main(mech_rows, hub_rows, pdf_path):
    """(a) operator-structure mechanism; (b) per-sweep efficiency vs N."""

    with ttns_style():
        fig, (ax_m, ax_e) = plt.subplots(1, 2, figsize=(7.0, 2.8))
        fig.subplots_adjust(left=0.12, right=0.98, bottom=0.20, top=0.88, wspace=0.42)

        pts = sort_rows(mech_rows, "n_total_sites")
        x = [float(r["n_total_sites"]) for r in pts]
        for field, color, label in (
            ("sop_local_factors", "#00529B", "SOP local factors"),
            ("ttno_tensor_elements", "#007A33", "TTNO tensor elements"),
        ):
            y = [float(r[field]) for r in pts]
            ax_m.plot(x, y, marker="o", color=color, label=label)
            alpha = fit_alpha(pts[-4:], "n_total_sites", field)
            ax_m.text(
                x[-1],
                y[-1],
                rf"  $\alpha={alpha:.2f}$",
                fontsize=7,
                color=color,
                va="center",
            )
        ax_m.text(
            0.03,
            0.97,
            r"TTNO max bond $=7$",
            transform=ax_m.transAxes,
            fontsize=7,
            ha="left",
            va="top",
            color="#007A33",
        )
        ax_m.set_xscale("log", base=2)
        ax_m.set_yscale("log")
        ax_m.set_xlabel(r"Total sites, $N$")
        ax_m.set_ylabel("Total operator factors / elements")
        label_panel(ax_m, "a", "Operator structure")
        finish_axis(ax_m)
        ax_m.legend(loc="upper left", frameon=False)

        for method in METHODS:
            pts = sort_rows(
                [r for r in hub_rows if r["method"] == method], "n_total_sites"
            )
            if len(pts) < 4:
                continue
            x = [float(r["n_total_sites"]) for r in pts]
            y = [float(r["time_total_mean_sec"]) for r in pts]
            ax_e.plot(
                x,
                y,
                marker=METHOD_MARKERS[method],
                color=METHOD_COLORS[method],
                label=METHOD_LABELS[method],
            )
            alpha = fit_alpha(pts[-4:], "n_total_sites", "time_total_mean_sec")
            ax_e.text(
                x[-1],
                y[-1],
                rf"  $\alpha={alpha:.2f}$",
                fontsize=7,
                color=METHOD_COLORS[method],
                va="center",
            )
            if method != "sop_no_env":
                power = REFERENCE_POWERS[method]
                xg = x
                yg = [y[-1] * (float(xi) / x[-1]) ** power for xi in xg]
                ax_e.plot(
                    xg,
                    yg,
                    linestyle="--",
                    color=METHOD_COLORS[method],
                    alpha=0.6,
                )
        ax_e.set_xscale("log", base=2)
        ax_e.set_yscale("log")
        ax_e.set_xlabel(r"Total sites, $N$")
        ax_e.set_ylabel("Per-sweep wall time (s)")
        label_panel(ax_e, "b", "Operator action efficiency")
        finish_axis(ax_e)
        ax_e.legend(loc="upper left", frameon=False)

        return save_pdf_png(fig, pdf_path)


def plot_si_li2024(li_rows, pdf_path):
    panels = (
        ("modes", "n_modes", r"Number of modes, $N_b$"),
        ("state_bond", "target_state_bond", r"State bond dimension, $M_s$"),
        ("primitive_basis", "primitive_basis_dim", r"Primitive basis, $d$"),
    )
    with ttns_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))
        fig.subplots_adjust(left=0.08, right=0.985, bottom=0.20, top=0.88, wspace=0.28)
        for ax, (panel, x_field, xlabel) in zip(axes, panels):
            all_x = []
            for method in METHODS:
                pts = sort_rows(
                    [r for r in li_rows if r["panel"] == panel and r["method"] == method],
                    x_field,
                )
                if not pts:
                    continue
                x = [float(r[x_field]) for r in pts]
                y = [float(r["time_total_mean_sec"]) for r in pts]
                ax.errorbar(
                    x,
                    y,
                    yerr=[float(r["time_total_std_sec"]) for r in pts],
                    capsize=2,
                    marker=METHOD_MARKERS[method],
                    color=METHOD_COLORS[method],
                    label=METHOD_LABELS[method],
                )
                power = REFERENCE_POWERS.get(method, 0.0) if panel == "modes" else None
                if panel == "state_bond":
                    power = 4.0
                elif panel == "primitive_basis":
                    power = 0.0
                xg = x[len(x) // 2 :] if panel != "modes" else x
                yg = [y[-1] * (float(xi) / x[-1]) ** power for xi in xg]
                ax.plot(xg, yg, linestyle="--", color=METHOD_COLORS[method], alpha=0.6)
                all_x.extend(x)
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.set_xlabel(xlabel)
            ax.set_ylabel("All-node action wall time (s)")
            label_panel(ax, chr(ord("a") + len(axes) - 3 + panels.index((panel, x_field, xlabel))), panel)
            finish_axis(ax)
        axes[0].legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def plot_si_stage(stage_rows, pdf_path):
    panels = (
        ("time_env_build_mean_sec", "time_apply_mean_sec", "Wall time (s)"),
        ("memory_peak_mean_mb", None, "Peak memory (MB)"),
        ("elements_per_apply_second", None, "State elements / apply s"),
    )
    with ttns_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))
        fig.subplots_adjust(left=0.08, right=0.985, bottom=0.20, top=0.88, wspace=0.30)
        for ax, (field_a, field_b, ylabel) in zip(axes, panels):
            for method in METHODS:
                pts = sort_rows(
                    [r for r in stage_rows if r["method"] == method], "n_modes"
                )
                if not pts:
                    continue
                x = [float(r["n_modes"]) for r in pts]
                ya = [float(r[field_a]) for r in pts]
                ax.plot(
                    x,
                    ya,
                    linestyle="-",
                    marker=METHOD_MARKERS[method],
                    color=METHOD_COLORS[method],
                    label=METHOD_LABELS[method],
                )
                if field_b is not None:
                    yb = [float(r[field_b]) for r in pts]
                    ax.plot(
                        x,
                        yb,
                        linestyle="--",
                        marker=METHOD_MARKERS[method],
                        color=METHOD_COLORS[method],
                        label=None,
                    )
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.set_xlabel(r"Number of modes, $N_b$")
            ax.set_ylabel(ylabel)
            label_panel(ax, chr(ord("a") + panels.index((field_a, field_b, ylabel))), "stage")
            finish_axis(ax)
        axes[0].legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def plot_si_construction(con_rows, pdf_path):
    panels = (
        ("modes", "n_modes", r"Number of modes, $N_b$"),
        ("state_bond", "target_state_bond", r"State bond dimension, $M_s$"),
        ("primitive_basis", "primitive_basis_dim", r"Primitive basis, $d$"),
    )
    with ttns_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8))
        fig.subplots_adjust(left=0.08, right=0.985, bottom=0.20, top=0.88, wspace=0.28)
        for ax, (panel, x_field, xlabel) in zip(axes, panels):
            pts = sort_rows([r for r in con_rows if r["panel"] == panel], x_field)
            if not pts:
                continue
            x = [float(r[x_field]) for r in pts]
            for method, color in (("sop", "#00529B"), ("ttno", "#007A33")):
                field = f"{method}_build_time_mean_sec"
                err = f"{method}_build_time_std_sec"
                y = [float(r[field]) for r in pts]
                ax.errorbar(
                    x,
                    y,
                    yerr=[float(r[err]) for r in pts],
                    capsize=2,
                    marker="o" if method == "sop" else "s",
                    color=color,
                    label="SOP baseline build" if method == "sop" else "TTNO build",
                )
            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Operator build wall time (s)")
            label_panel(ax, chr(ord("a") + panels.index((panel, x_field, xlabel))), panel)
            finish_axis(ax)
        axes[0].legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def plot_si_mechanism(mech_rows, pdf_path):
    with ttns_style():
        fig, (ax_s, ax_c) = plt.subplots(1, 2, figsize=(7.0, 2.8))
        fig.subplots_adjust(left=0.12, right=0.98, bottom=0.20, top=0.88, wspace=0.42)
        pts = sort_rows(mech_rows, "n_total_sites")
        x = [float(r["n_total_sites"]) for r in pts]
        ax_s.plot(x, [float(r["support_mean"]) for r in pts], marker="o", color="#00529B", label="mean support")
        ax_s.plot(x, [float(r["support_max"]) for r in pts], marker="s", color="#CC0000", label="max support")
        ax_s.set_xscale("log", base=2)
        ax_s.set_yscale("log")
        ax_s.set_xlabel(r"Total sites, $N$")
        ax_s.set_ylabel("Non-trivial local ops per SOP term")
        label_panel(ax_s, "a", "SOP term support")
        finish_axis(ax_s)
        ax_s.legend(loc="upper left", frameon=False)

        ax_c.plot(x, [float(r["sop_local_factors"]) for r in pts], marker="o", color="#00529B", label="SOP local factors")
        ax_c.plot(x, [float(r["ttno_tensor_elements"]) for r in pts], marker="s", color="#007A33", label="TTNO tensor elements")
        ax_c.set_xscale("log", base=2)
        ax_c.set_yscale("log")
        ax_c.set_xlabel(r"Total sites, $N$")
        ax_c.set_ylabel("Total operator factors / elements")
        label_panel(ax_c, "b", "SOP factors vs TTNO elements")
        finish_axis(ax_c)
        ax_c.legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def plot_si_cost(cost_rows, pdf_path):
    panels = (
        ("time_per_sweep_mean_sec", "Per-sweep wall time (s)", True),
        ("memory_peak_mean_mb", "Peak memory (MB)", False),
        ("memory_time_product_mb_s", "Memory x time (MB s)", False),
        ("speedup_vs_ttno", "Speedup vs TTNO", False),
    )
    with ttns_style():
        fig, axes = plt.subplots(2, 2, figsize=(7.0, 5.4))
        fig.subplots_adjust(left=0.13, right=0.98, bottom=0.12, top=0.95, wspace=0.35, hspace=0.55)
        for ax, (field, ylabel, guides) in zip(axes.ravel(), panels):
            ttno_by_n = {
                float(r["n_total_sites"]): float(r["time_per_sweep_mean_sec"])
                for r in cost_rows
                if r["method"] == "ttno_with_env"
            }
            for method in METHODS:
                pts = sort_rows(
                    [r for r in cost_rows if r["method"] == method], "n_total_sites"
                )
                if not pts:
                    continue
                x = [float(r["n_total_sites"]) for r in pts]
                if field == "speedup_vs_ttno":
                    if method == "ttno_with_env":
                        continue
                    y = [
                        float(r["time_per_sweep_mean_sec"]) / ttno_by_n[float(r["n_total_sites"])]
                        for r in pts
                        if float(r["n_total_sites"]) in ttno_by_n
                    ]
                    x = [
                        float(r["n_total_sites"])
                        for r in pts
                        if float(r["n_total_sites"]) in ttno_by_n
                    ]
                else:
                    y = [float(r[field]) for r in pts]
                ax.plot(
                    x,
                    y,
                    marker=METHOD_MARKERS[method],
                    color=METHOD_COLORS[method],
                    label=METHOD_LABELS[method],
                )
                if guides:
                    power = REFERENCE_POWERS[method]
                    ax.plot(x, [y[-1] * (float(xi) / x[-1]) ** power for xi in x], linestyle="--", color=METHOD_COLORS[method], alpha=0.6)
            ax.set_xscale("log", base=2)
            if field != "speedup_vs_ttno":
                ax.set_yscale("log")
            ax.set_xlabel(r"Total sites, $N$")
            ax.set_ylabel(ylabel)
            label_panel(ax, chr(ord("a") + panels.index((field, ylabel, guides))), field)
            finish_axis(ax)
        axes[0, 0].legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def plot_si_hubbard(hub_rows, pdf_path):
    with ttns_style():
        fig, ax = plt.subplots(figsize=(3.5, 2.8))
        for method in METHODS:
            pts = sort_rows(
                [r for r in hub_rows if r["method"] == method], "n_total_sites"
            )
            if not pts:
                continue
            x = [float(r["n_total_sites"]) for r in pts]
            y = [float(r["time_total_mean_sec"]) for r in pts]
            ax.errorbar(
                x,
                y,
                yerr=[float(r["time_total_std_sec"]) for r in pts],
                capsize=2,
                marker=METHOD_MARKERS[method],
                color=METHOD_COLORS[method],
                label=METHOD_LABELS[method],
            )
            power = REFERENCE_POWERS[method]
            ax.plot(x, [y[-1] * (float(xi) / x[-1]) ** power for xi in x], linestyle="--", color=METHOD_COLORS[method], alpha=0.6)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xlabel(r"Total sites, $N$")
        ax.set_ylabel("Per-sweep wall time (s)")
        label_panel(ax, "a", "Hubbard balanced")
        finish_axis(ax)
        ax.legend(loc="upper left", frameon=False)
        return save_pdf_png(fig, pdf_path)


def generate(figures_dir):
    figures_dir = Path(figures_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    result_root = Path("benchmarks/results/operator_env_scaling/final")

    hub_rows = read_csv(result_root / "hubbard_junction_20260806_hubbard_summary.csv")
    mech_rows = read_csv(result_root / "hubbard_junction_20260806_mechanism_summary.csv")
    outputs = [
        plot_main(
            mech_rows,
            hub_rows,
            figures_dir / "Fig_Main_Mechanism_Efficiency.pdf",
        ),
        plot_si_li2024(
            read_csv(result_root / "li2024_spin_boson_20260713_summary.csv"),
            figures_dir / "Fig_SI_Li2024_Scaling.pdf",
        ),
        plot_si_stage(
            read_csv(result_root / "li2024_spin_boson_20260713_stage_summary.csv"),
            figures_dir / "Fig_SI_Stage_Breakdown.pdf",
        ),
        plot_si_construction(
            read_csv(result_root / "li2024_spin_boson_20260713_construction_summary.csv"),
            figures_dir / "Fig_SI_Construction.pdf",
        ),
        plot_si_mechanism(
            read_csv(result_root / "hubbard_junction_20260806_mechanism_summary.csv"),
            figures_dir / "Fig_SI_JW_Mechanism.pdf",
        ),
        plot_si_cost(
            read_csv(result_root / "hubbard_junction_20260806_cost_summary.csv"),
            figures_dir / "Fig_SI_Cost_Metrics.pdf",
        ),
        plot_si_hubbard(hub_rows, figures_dir / "Fig_SI_Hubbard_Scaling.pdf"),
    ]
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=Path("benchmarks/results/operator_env_scaling/figures"),
    )
    args = parser.parse_args()
    outputs = generate(args.figures_dir)
    for pdf, png in outputs:
        print(f"Wrote {pdf} and {png}")


if __name__ == "__main__":
    main()
