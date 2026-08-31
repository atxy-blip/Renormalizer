#!/usr/bin/env python3
"""Plot the redesigned Figure 3 operator-scaling figure from raw CSVs.

Consumes the raw benchmark CSVs produced by
``benchmark_adaptive_operator_env.py`` (Fig 3 redesign jobs) and produces

    <output-prefix>.pdf                  three-panel figure
    <output-prefix>_fits_summary.csv     every largest-four-point fit used

Panels
------
(a) Per-sweep wall time versus site count N for the three operator paths on the
    bridge-centered tree without the Hubbard term (U_d = 0), with the dashed
    theoretical guides labelled as N^3, N^2 and N^1.
(b) The same three paths with the two-body Hubbard term switched on
    (U_d = 1 eV).  Turning U_d on adds one SOP term and leaves all three
    exponents where they were, so panel (b) is deliberately a near-copy of
    panel (a): the operator cost is set by the operator *structure*, not by the
    interaction strength.
(c) Jordan-Wigner control on one fixed tree.  Both series use the identical
    spin-blocked orbital layout and the identical Hamiltonian (same spectrum to
    machine precision); they differ only in the linear order along which the
    Jordan-Wigner strings are laid.  Rebuilding the transformation in tree order
    keeps the TTNO bond dimension constant and the cost at N^1; keeping the
    stale energy-ordered strings makes the TTNO bond grow linearly with N and
    the cost approaches N^2.  The SOP path never sees the difference.  Inset:
    TTNO bond dimension versus N for the two orderings.

    Panel (c) runs one N further than (a)/(b) (N = 546 rather than 274): the
    stale-JW cost only reaches its asymptotic slope above N ~ 300, so a window
    ending at 274 still averages over the crossover.  It also omits sop_no_env,
    whose exponent (a)/(b) already establish and whose cost at these sizes is
    what would make the extra point unaffordable.

Fit convention: repeat median per (method, U_d, topology, layout, JW ordering,
N); log-log linear fit over the largest four usable points of each series (the
published convention, e.g. N = 19-138 for sop_no_env and N = 36-274 otherwise).
"""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# Nature-style plotting configuration.
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.figsize": (3.5, 3.0),
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.top": True,
    "ytick.right": True,
    "legend.frameon": False,
    "lines.linewidth": 1.2,
    "lines.markersize": 4,
})

METHOD_ORDER = ("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")
METHOD_LABEL = {
    "sop_no_env": "SOP, no env",
    "sop_mctdh_like_state_env": "SOP with env",
    "ttno_with_env": "TTNO",
}
METHOD_COLOR = {
    "sop_no_env": "#c44e52",
    "sop_mctdh_like_state_env": "#4c72b0",
    "ttno_with_env": "#55a868",
}
THEORY_ALPHA = {"sop_no_env": 3.0, "sop_mctdh_like_state_env": 2.0, "ttno_with_env": 1.0}

# CSVs written before the orbital-layout / JW-ordering knobs existed carry the
# defaults implicitly; panels (a) and (b) read those runs unchanged.
DEFAULT_LAYOUT = "energy"
DEFAULT_JW = "tree_order"

# Panel (b) is the Hubbard-on twin of panel (a).
PANEL_A_UD = 0.0
PANEL_B_UD = 1.0

# Panel (c) holds the tree and the layout fixed and varies only the JW ordering.
PANEL_C_LAYOUT = "spin_blocked"
# The two JW labels describe the linear order along which the transformation
# strings are laid.  Tree order rebuilds the strings for the tree's own leaf
# order, so every subtree spans a contiguous stretch of the JW line.  Energy
# order keeps the energy-sorted strings from the panel (a)/(b) layout even
# after the orbitals are re-blocked by spin.  Same Hamiltonian, same spectrum,
# same tree -- only the operator's compressibility differs.
JW_LABEL = {
    "tree_order": "tree order",
    "energy_order": "energy order",
}
JW_STYLE = {
    "tree_order": {"marker": "o", "ls": "-", "mfc": None},
    "energy_order": {"marker": "s", "ls": "--", "mfc": "none"},
}
PANEL_C_METHODS = ("sop_mctdh_like_state_env", "ttno_with_env")
# Theoretical guide per (method, JW ordering) in panel (c): the TTNO cost tracks
# the TTNO bond dimension (constant -> N^1, growing like N -> N^2), while the
# SOP cost is blind to the ordering.
PANEL_C_THEORY = {
    ("ttno_with_env", "tree_order"): 1.0,
    ("ttno_with_env", "energy_order"): 2.0,
}

# Position of each dashed guide's "∝ N^k" label, given directly in DATA
# coordinates: (site count N, per-sweep wall time in seconds).  Both axes are
# logarithmic, so doubling a value moves the label by a factor of two, not by
# "two units".  The coordinate is the lower-left corner of the text box
# (ha="left", va="bottom" below); flip those to anchor a different corner.
LABEL_POS = {
    "sop_no_env":               (110, 800),
    "sop_mctdh_like_state_env": (140.0, 30),
    "ttno_with_env":            (140.0, 0.183),
}
PROPTO_FONTSIZE = 12
# Panel (c) guides are drawn over this many trailing points only, and labelled
# in the right-hand margin at the end of their own curve (see panel_jw_ordering)
# rather than at hand-tuned coordinates, so the labels follow the data when the
# plotted N range changes.
GUIDE_POINTS = 3
GUIDE_LABEL_XSHIFT = 1
GUIDE_LABEL_YSHIFT = 1.5
PANEL_C_XMARGIN = 1


def read_rows(csv_paths, max_n=None):
    rows = []
    for path in csv_paths:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if row.get("quantity") != "local_effective_1site_apply_all_nodes":
                    continue
                if not str(row.get("status", "")).startswith("ok"):
                    continue
                if max_n is not None and int(float(row["n_total_sites"])) > max_n:
                    continue
                rows.append(row)
    if not rows:
        raise SystemExit("no usable all-node rows found in the given CSVs")
    return rows


def row_key(row):
    return (
        row["method"],
        float(row["ud_ev"]),
        row["tree_topology"],
        row.get("orbital_layout") or DEFAULT_LAYOUT,
        row.get("jw_ordering") or DEFAULT_JW,
        int(float(row["n_total_sites"])),
    )


def group_medians(rows):
    """Median wall time and TTNO bond per (method, ud, topology, layout, jw, N)."""
    times = defaultdict(list)
    bonds = defaultdict(list)
    for row in rows:
        key = row_key(row)
        times[key].append(float(row["time_total_sec"]))
        if row["method"] == "ttno_with_env" and row.get("ttno_max_bond"):
            bonds[key].append(float(row["ttno_max_bond"]))
    med = {k: float(np.median(v)) for k, v in times.items()}
    med_bond = {k: float(np.median(v)) for k, v in bonds.items()}
    return med, med_bond


def largest_four_fit(x, y):
    """Log-log linear fit over the largest four points; returns dict."""
    if len(x) < 2:
        return {"alpha": np.nan, "alpha_se": np.nan, "n_points": len(x),
                "window": "", "r2": np.nan}
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    order = np.argsort(x)
    x, y = x[order], y[order]
    used_x, used_y = x[-4:], y[-4:]
    lx, ly = np.log(used_x), np.log(used_y)
    (alpha, intercept), cov = np.polyfit(lx, ly, 1, cov=True)
    resid = ly - (alpha * lx + intercept)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((ly - ly.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan
    window = f"{int(used_x.min())}-{int(used_x.max())}"
    return {
        "alpha": float(alpha),
        "alpha_se": float(np.sqrt(cov[0, 0])),
        "n_points": len(used_x),
        "window": window,
        "r2": r2,
    }


def series_for(table, method, ud, topology,
               layout=DEFAULT_LAYOUT, jw=DEFAULT_JW):
    keys = sorted(
        (k for k in table
         if k[0] == method and k[1] == ud and k[2] == topology
         and k[3] == layout and k[4] == jw),
        key=lambda k: k[5],
    )
    if not keys:
        return None, None
    x = np.array([k[5] for k in keys], dtype=float)
    y = np.array([table[k] for k in keys], dtype=float)
    return x, y


def reference_line(x_anchor, y_anchor, alpha, x):
    return y_anchor * (x / x_anchor) ** alpha


def guide_label(ax, pos, alpha, color):
    """Annotate a dashed guide with its theoretical power at DATA position pos."""
    ax.text(pos[0], pos[1], rf"$\propto N^{{{alpha:g}}}$", color=color,
            fontsize=PROPTO_FONTSIZE, ha="left", va="bottom")


def panel_methods(ax, med, ud, panel, title, fit_rows):
    """Wall time versus N for the three operator paths at one U_d (panels a, b)."""
    plotted = False
    for method in METHOD_ORDER:
        x, y = series_for(med, method, ud, "bridge_centered")
        if x is None:
            continue
        plotted = True
        fit_rows.append({
            "panel": panel, "method": method, "ud_ev": ud,
            "tree_topology": "bridge_centered",
            "orbital_layout": DEFAULT_LAYOUT, "jw_ordering": DEFAULT_JW,
            **largest_four_fit(x, y),
        })
        ax.plot(x, y, "o-", color=METHOD_COLOR[method],
                label=METHOD_LABEL[method])
        y_ref = reference_line(x[-1], y[-1], THEORY_ALPHA[method], x)
        ax.plot(x, y_ref, "--", color=METHOD_COLOR[method], alpha=0.6)
        # Label each dashed guide with its theoretical power instead of the
        # fitted exponent; position comes from LABEL_POS at the top of the file.
        guide_label(ax, LABEL_POS[method], THEORY_ALPHA[method], METHOD_COLOR[method])
    if not plotted:
        raise SystemExit(
            f"panel ({panel}) has no data: expected bridge_centered rows at "
            f"U_d = {ud:g} with orbital_layout={DEFAULT_LAYOUT!r} and "
            f"jw_ordering={DEFAULT_JW!r}."
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("site count $N$")
    ax.set_ylabel("per-sweep wall time (s)")
    ax.set_title(f"({panel}) {title}")
    ax.legend(frameon=False)
    ax.grid(True, which="both", alpha=0.25)


def panel_jw_ordering(ax, med, med_bond, fit_rows):
    """Panel (c): one tree, one layout, two Jordan-Wigner orderings."""
    lo, hi = np.inf, 0.0
    x_lo, x_hi = np.inf, 0.0
    plotted = False
    for method in PANEL_C_METHODS:
        for jw in ("tree_order", "energy_order"):
            x, y = series_for(med, method, PANEL_A_UD, "bridge_centered",
                              layout=PANEL_C_LAYOUT, jw=jw)
            if x is None:
                continue
            plotted = True
            lo, hi = min(lo, y.min()), max(hi, y.max())
            x_lo, x_hi = min(x_lo, x.min()), max(x_hi, x.max())
            fit_rows.append({
                "panel": "c", "method": method, "ud_ev": PANEL_A_UD,
                "tree_topology": "bridge_centered",
                "orbital_layout": PANEL_C_LAYOUT, "jw_ordering": jw,
                **largest_four_fit(x, y),
            })
            style = JW_STYLE[jw]
            ax.plot(x, y, marker=style["marker"], ls=style["ls"],
                    color=METHOD_COLOR[method],
                    markerfacecolor=style["mfc"] or METHOD_COLOR[method],
                    label=f"{METHOD_LABEL[method]}, {JW_LABEL[jw]}")
            alpha = PANEL_C_THEORY.get((method, jw))
            if alpha is not None:
                # Guide over the fit window only: anchored at the last point, a
                # full-range guide would run far below the small-N data, where
                # the cost has not yet reached its asymptotic power.
                xg = x[-GUIDE_POINTS:]
                ax.plot(xg, reference_line(x[-1], y[-1], alpha, xg), ":",
                        color="0.3")
                ax.text(x[-1] * GUIDE_LABEL_XSHIFT,
                        y[-1] * GUIDE_LABEL_YSHIFT,
                        rf"$\propto N^{{{alpha:g}}}$", color="0.25",
                        fontsize=PROPTO_FONTSIZE, ha="left", va="center")
    if not plotted:
        raise SystemExit(
            "panel (c) has no data: expected rows with orbital_layout="
            f"{PANEL_C_LAYOUT!r} and jw_ordering in ('tree_order', 'energy_order'). "
            "Run benchmarks/scripts/submit_fig3_redesign.sh panel_c."
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    # Headroom below the data so the inset never lands on the TTNO curves, and
    # to the right so the guide labels sit clear of the axes frame.
    ax.set_ylim(lo / 12.0, 1e4)
    ax.set_xlim(x_lo / 1.2, x_hi * PANEL_C_XMARGIN)
    ax.set_xlabel("site count $N$")
    ax.set_ylabel("per-sweep wall time (s)")
    ax.set_title("(c) JW ordering: tree vs energy")
    # One legend entry per plotted curve, drawn in that curve's own style: a
    # two-part "colour = method, marker = ordering" key reads ambiguously here,
    # because the method swatches collide with the tree-order marker style.
    ax.legend(frameon=False, loc="upper left",
              handlelength=2.4, borderpad=0.2, labelspacing=0.35)
    ax.grid(True, which="both", alpha=0.25)

    inset = ax.inset_axes([0.65, 0.1, 0.33, 0.2])
    for jw in ("energy_order", "tree_order"):
        x, y = series_for(med_bond, "ttno_with_env", PANEL_A_UD, "bridge_centered",
                          layout=PANEL_C_LAYOUT, jw=jw)
        if x is None:
            continue
        style = JW_STYLE[jw]
        inset.plot(x, y, marker=style["marker"], ls=style["ls"], ms=2.5,
                   color=METHOD_COLOR["ttno_with_env"], lw=1.0,
                   markerfacecolor=style["mfc"] or METHOD_COLOR["ttno_with_env"])
    inset.set_xscale("log")
    inset.set_yscale("log")
    inset.tick_params(labelsize=5.5, pad=1.5)
    inset.set_xlabel("$N$", fontsize=6, labelpad=0)
    inset.set_title("TTNO bond dim. $D$", fontsize=6.5, pad=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, default=None,
                        help="Directory containing the job raw CSVs.")
    parser.add_argument("--csv", nargs="*", type=Path, default=[],
                        help="Explicit raw CSV paths (alternative to --csv-dir).")
    parser.add_argument("--output", type=Path, required=True,
                        help="Output PDF path (fits CSV written beside it).")
    parser.add_argument("--png", action="store_true",
                        help="Also write a PNG preview beside the PDF.")
    parser.add_argument("--max-n", type=int, default=None,
                        help="Drop every point above this site count. Use to "
                             "preview the figure without the most expensive N.")
    args = parser.parse_args()

    csv_paths = list(args.csv)
    if args.csv_dir is not None:
        csv_paths += sorted(args.csv_dir.glob("*_raw.csv"))
    if not csv_paths:
        raise SystemExit("no input CSVs given")

    rows = read_rows(csv_paths, max_n=args.max_n)
    med, med_bond = group_medians(rows)
    print(f"Read {len(csv_paths)} CSV(s), {len(rows)} usable rows, "
          f"{len(med)} (method, U_d, topology, layout, JW, N) groups.")

    fig, axes = plt.subplots(1, 3, figsize=(3.5 * 3, 3.0))
    fit_rows = []
    panel_methods(axes[0], med, PANEL_A_UD, "a",
                  rf"$U_d={PANEL_A_UD:g}$", fit_rows)
    panel_methods(axes[1], med, PANEL_B_UD, "b",
                  rf"$U_d={PANEL_B_UD:g}$ eV", fit_rows)
    panel_jw_ordering(axes[2], med, med_bond, fit_rows)
    fig.tight_layout()
    fig.savefig(args.output)
    print(f"Wrote {args.output}")
    if args.png:
        png_path = args.output.with_suffix(".png")
        fig.savefig(png_path, dpi=200)
        print(f"Wrote {png_path}")

    fits_path = args.output.with_suffix("").with_name(args.output.stem + "_fits_summary.csv")
    with open(fits_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "panel", "method", "ud_ev", "tree_topology", "orbital_layout",
            "jw_ordering", "alpha", "alpha_se", "r2", "n_points", "window",
        ])
        writer.writeheader()
        for row in sorted(fit_rows, key=lambda r: (r["panel"], r["method"], r["ud_ev"])):
            writer.writerow(row)
    print(f"Wrote {fits_path}")
    for row in fit_rows:
        print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
