#!/usr/bin/env python3
"""Collect Hubbard per-node snapshots and produce the SI profile figure."""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from benchmarks.hubbard_pernode_manifest import PERNODE_POINTS
from benchmarks.run_hubbard_pernode_point import load_snapshot


def collect_snapshots(snapshot_dir):
    return [load_snapshot(path) for path in sorted(Path(snapshot_dir).rglob("*.npz"))]


def flatten(snapshots):
    rows = []
    for snap in snapshots:
        if snap.get("status") != "ok":
            continue
        for row in snap["rows"]:
            rows.append({
                "n_lead": snap["n_lead"],
                "n_phonon": snap["n_phonon"],
                "n_total_sites": snap["n_total_sites"],
                **row,
            })
    return rows


def pearson_log(xs, ys):
    lx = np.log(np.asarray(xs, dtype=float))
    ly = np.log(np.asarray(ys, dtype=float))
    return float(np.corrcoef(lx, ly)[0, 1])


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


def plot(rows, pdf_path):
    with matplotlib.rc_context({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
        "axes.linewidth": 0.8,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "legend.frameon": False,
        "lines.linewidth": 1.2,
        "lines.markersize": 4.0,
    }):
        fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 2.8))
        fig.subplots_adjust(left=0.12, right=0.98, bottom=0.20, top=0.88, wspace=0.42)

        target = max(rows, key=lambda r: r["n_total_sites"])["n_total_sites"]
        point_rows = [r for r in rows if r["n_total_sites"] == target]
        point_rows.sort(key=lambda r: r["node_idx"])
        methods = (
            ("time_no_env_sec", "#00529B", "SOP no env", "o"),
            ("time_strict_env_sec", "#CC0000", "SOP strict env", "o"),
            ("time_ttno_sec", "#007A33", "TTNO + env", "s"),
        )
        for field, color, label, marker in methods:
            x = [r["node_idx"] for r in point_rows]
            y = [float(r[field]) for r in point_rows]
            ax_a.plot(x, y, marker=marker, color=color, label=label, linestyle="none")
        ax_a.axvspan(
            min(r["node_idx"] for r in point_rows if r["node_role"] == "bridge"),
            max(r["node_idx"] for r in point_rows if r["node_role"] == "bridge"),
            color="0.9",
            zorder=0,
        )
        ax_a.set_yscale("log")
        ax_a.set_xlabel("Tree node index")
        ax_a.set_ylabel("Per-node local action (s)")
        ax_a.set_title("(a) Per-node wall time", loc="left")
        ax_a.legend(loc="upper left", frameon=False)

        for field, color, label, marker in methods[:2]:
            x = [float(r["support_load"]) for r in point_rows]
            y = [float(r[field]) for r in point_rows]
            ax_b.plot(x, y, marker=marker, color=color, label=label, linestyle="none")
        ttno_med = float(np.median([r["time_ttno_sec"] for r in point_rows]))
        ax_b.axhline(ttno_med, color="#007A33", linestyle="--", linewidth=1.0, label="TTNO median")
        xs = [float(r["support_load"]) for r in point_rows]
        ys = [float(r["time_no_env_sec"]) for r in point_rows]
        pairs = [(x, y) for x, y in zip(xs, ys) if x > 0]
        rho = pearson_log([p[0] for p in pairs], [p[1] for p in pairs])
        ax_b.text(
            0.05,
            0.95,
            rf"$\rho(\log N_{{load}},\log t)={rho:.2f}$",
            transform=ax_b.transAxes,
            fontsize=7,
            va="top",
        )
        ax_b.text(
            0.05,
            0.86,
            "no local-load dependence:\n"
            "SOP no-env pays per-term\nglobal traversal at every node",
            transform=ax_b.transAxes,
            fontsize=6.5,
            va="top",
            color="0.25",
        )
        ax_b.set_xscale("log")
        ax_b.set_yscale("log")
        ax_b.set_xlabel("SOP term load per node")
        ax_b.set_ylabel("Per-node local action (s)")
        ax_b.set_title("(b) Cost vs SOP load", loc="left")
        ax_b.legend(loc="upper left", frameon=False)

        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        png_path = pdf_path.with_suffix(".png")
        fig.savefig(pdf_path, format="pdf", transparent=True)
        fig.savefig(png_path, format="png", dpi=300, transparent=True)
        plt.close(fig)
        return pdf_path, png_path


def generate(rows, output_prefix, figures_dir=None):
    flat = flatten(rows)
    if not flat:
        raise RuntimeError("no ok per-node rows")
    _write_csv(output_prefix.with_name(output_prefix.name + "_pernode_summary.csv"), flat)
    if figures_dir is None:
        pdf_path = output_prefix.with_name(output_prefix.name + "_pernode_profile.pdf")
    else:
        pdf_path = Path(figures_dir) / "Fig_SI_PerNode_Profile.pdf"
    pdf, png = plot(flat, pdf_path)
    return flat, pdf, png


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    snaps = collect_snapshots(args.snapshot_dir)
    ok = [s for s in snaps if s.get("status") == "ok"]
    if len(ok) != len(PERNODE_POINTS) and not args.allow_partial:
        raise RuntimeError(f"expected {len(PERNODE_POINTS)} ok snapshots, got {len(ok)}")
    flat, pdf, png = generate(snaps, args.output_prefix, args.figures_dir)
    print(f"Collected {len(ok)}/{len(PERNODE_POINTS)} snapshots; wrote {len(flat)} rows, {pdf}, {png}")


if __name__ == "__main__":
    main()
