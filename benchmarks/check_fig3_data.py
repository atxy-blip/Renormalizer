#!/usr/bin/env python3
"""Validate the Fig 3 redesign benchmark CSVs before plotting.

Checks, per CSV family:

  1. all usable rows have relative_error_vs_ttno below 1e-12 (machine
     precision claim; expected ~1e-15) and status ok;
  2. panel (a)/(b) baseline (energy layout, tree-order JW): ttno_max_bond == 7
     at every N (the manuscript's constant-bond claim);
  3. panel (c): on the spin-blocked layout, tree-order JW keeps ttno_max_bond
     constant while stale energy-order JW makes it grow linearly with N (the
     deviation signal that drives the N^1 -> N^2 jump);
  4. SOP term count == 12 n_lead + 4 n_phonon at U_d = 0 and one more for
     U_d > 0 (the Hubbard term), for every layout and JW ordering -- the
     ordering permutes the Jordan-Wigner strings, it never adds terms;
  5. state_max_bond == 20 and the local basis summary contains SHO:10
     (M_s=20, d=10 settings);
  6. completeness of the panel (a)/(b) U x N x method x repeat grid, tolerating
     the documented sop_no_env (64,16) budget omission, and of the panel (c)
     JW-ordering x N grid;
  7. (informational) largest-four-point exponents per method at U=0 baseline,
     to compare with the published 3.18/2.08/1.04, plus the panel (c) TTNO
     exponents (expected ~1 and ~2).

Usage: python check_fig3_data.py --csv-dir <dir>  [--csv file1 file2 ...]
Exit code 0 only if all hard checks pass.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

EXPECTED_N = {19: (4, 1), 36: (8, 2), 70: (16, 4), 138: (32, 8), 274: (64, 16)}
# Panel (c) carries one point beyond the (a)/(b) range to reach the asymptotic
# stale-JW slope; see the plotter docstring.
EXPECTED_N_C = {**EXPECTED_N, 546: (128, 32)}
PANEL_AB_U = {0.0, 1.0}
METHODS = ("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")
PANEL_C_METHODS = ("sop_mctdh_like_state_env", "ttno_with_env")
PANEL_C_LAYOUT = "spin_blocked"
DEFAULT_LAYOUT = "energy"
DEFAULT_JW = "tree_order"
FAILS = []
INFOS = []


def fail(msg):
    FAILS.append(msg)


def info(msg):
    INFOS.append(msg)


def layout_of(row):
    return row.get("orbital_layout") or DEFAULT_LAYOUT


def jw_of(row):
    return row.get("jw_ordering") or DEFAULT_JW


def is_baseline(row):
    """Panel (a)/(b) family: physics-aware tree, energy layout, tree-order JW."""
    return (row["tree_topology"] == "bridge_centered"
            and layout_of(row) == DEFAULT_LAYOUT and jw_of(row) == DEFAULT_JW)


def load(paths):
    rows = []
    for p in paths:
        with open(p, newline="") as f:
            rows.extend(list(csv.DictReader(f)))
    ok = [r for r in rows if r.get("quantity") == "local_effective_1site_apply_all_nodes"
          and str(r.get("status", "")).startswith("ok")]
    nonok = [r for r in rows if r.get("quantity") == "local_effective_1site_apply_all_nodes"
             and not str(r.get("status", "")).startswith("ok")
             and r.get("method") != "point_setup"]
    return ok, nonok


def largest_four_alpha(x, y):
    order = np.argsort(x)
    x, y = x[order], y[order]
    x, y = x[-4:], y[-4:]
    alpha, _ = np.polyfit(np.log(x), np.log(y), 1)
    return float(alpha), (int(x.min()), int(x.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", type=Path, default=None)
    ap.add_argument("--csv", nargs="*", type=Path, default=[])
    args = ap.parse_args()

    paths = list(args.csv)
    if args.csv_dir is not None:
        paths += sorted(args.csv_dir.glob("*_raw.csv"))
    if not paths:
        print("FAIL: no CSVs given")
        return 2
    ok, nonok = load(paths)
    print(f"read {len(paths)} csv(s): {len(ok)} ok rows, {len(nonok)} non-ok rows")

    # 1. precision
    bad_prec = [r for r in ok if r.get("relative_error_vs_ttno") and
                abs(float(r["relative_error_vs_ttno"])) > 1e-12]
    if bad_prec:
        fail(f"{len(bad_prec)} ok rows with |rel_err| > 1e-12")
    else:
        info("precision: all ok rows have |rel_err| <= 1e-12")

    # 2/3. bond dimension per (layout, JW ordering) family
    bond = defaultdict(list)
    for r in ok:
        if r["method"] != "ttno_with_env" or not r.get("ttno_max_bond"):
            continue
        key = (r["tree_topology"], layout_of(r), jw_of(r),
               int(float(r["n_total_sites"])))
        bond[key].append(float(r["ttno_max_bond"]))

    def medians_for(topology, layout, jw):
        sites = sorted({k[3] for k in bond
                        if k[0] == topology and k[1] == layout and k[2] == jw})
        return {n: float(np.median(bond[(topology, layout, jw, n)])) for n in sites}

    baseline = medians_for("bridge_centered", DEFAULT_LAYOUT, DEFAULT_JW)
    if not baseline:
        fail("no baseline (energy layout, tree-order JW) ttno rows")
    else:
        info(f"baseline ttno bond medians: {baseline}")
        if any(abs(v - 7.0) > 1e-9 for v in baseline.values()):
            fail(f"baseline ttno bond not constant 7: {baseline}")

    aligned = medians_for("bridge_centered", PANEL_C_LAYOUT, "tree_order")
    stale = medians_for("bridge_centered", PANEL_C_LAYOUT, "energy_order")
    if not aligned or not stale:
        fail("panel (c) needs both spin_blocked/tree_order and "
             f"spin_blocked/energy_order ttno rows (got {len(aligned)} and {len(stale)})")
    else:
        info(f"panel (c) JW tree-order bond medians:   {aligned}")
        info(f"panel (c) JW energy-order bond medians: {stale}")
        if len(set(aligned.values())) != 1:
            fail(f"panel (c) tree-order JW bond not constant in N: {aligned}")
        sites = sorted(stale)
        vals = [stale[n] for n in sites]
        if any(b < a for a, b in zip(vals, vals[1:])):
            fail(f"panel (c) energy-order JW bond not nondecreasing: {vals}")
        if len(vals) > 1 and vals[-1] <= vals[0]:
            fail(f"panel (c) energy-order JW bond does not grow with N: {vals}")
        shared = sorted(set(aligned) & set(stale))
        if shared and any(stale[n] <= aligned[n] for n in shared):
            fail(f"panel (c) energy-order JW bond not above tree-order at every "
                 f"shared N: {[(n, aligned[n], stale[n]) for n in shared]}")
        if len(sites) >= 2:
            growth = np.polyfit(np.log(sites), np.log(vals), 1)[0]
            info(f"panel (c) energy-order JW bond grows like N^{growth:.2f} "
                 "(expected ~1)")
            if not 0.8 <= growth <= 1.25:
                fail(f"panel (c) energy-order JW bond growth exponent {growth:.2f} "
                     "outside [0.8, 1.25]")

    # 4. term counts -- invariant under layout and JW ordering
    for r in ok:
        n, m = int(float(r["n_lead"])), int(float(r["n_phonon"]))
        expected = 12 * n + 4 * m + (0 if float(r["ud_ev"]) == 0.0 else 1)
        got = int(float(r["n_sop_terms"]))
        if got != expected:
            fail(f"term count {got} != {expected} at (n_lead={n}, n_phonon={m}, "
                 f"U={r['ud_ev']}, layout={layout_of(r)}, jw={jw_of(r)})")
            break
    else:
        info("term counts match 12n_lead+4n_phonon(+1 Hubbard at U>0) in every family")

    # 5. M_s and d settings
    for r in ok:
        if abs(float(r["state_max_bond"]) - 20.0) > 1e-9:
            fail(f"state_max_bond {r['state_max_bond']} != 20 at N={r['n_total_sites']}")
            break
        summary = r.get("local_basis_summary") or "{}"
        try:
            counts = json.loads(summary)
        except Exception:
            fail(f"unparseable local_basis_summary: {summary!r}")
            break
        if counts.get("BasisSHO:10", 0) < 1:
            fail(f"d=10 missing from local_basis_summary: {summary}")
            break
    else:
        info("settings: M_s=20 and d=10 recorded everywhere")

    # 6a. completeness of the panel (a)/(b) grid
    grid = defaultdict(set)
    for r in ok:
        if is_baseline(r):
            grid[(float(r["ud_ev"]), r["method"])].add(
                (int(float(r["n_lead"])), int(float(r["n_phonon"]))))
    for ud in sorted(PANEL_AB_U):
        for method in METHODS:
            have = grid.get((ud, method), set())
            missing = set(EXPECTED_N.values()) - have
            if missing == {(64, 16)} and method == "sop_no_env":
                info(f"U={ud} {method}: documented (64,16) omission only")
            elif missing:
                fail(f"U={ud} {method}: missing points {sorted(missing)}")

    # 6b. completeness of the panel (c) grid
    grid_c = defaultdict(set)
    for r in ok:
        if r["tree_topology"] == "bridge_centered" and layout_of(r) == PANEL_C_LAYOUT:
            grid_c[(jw_of(r), r["method"])].add(
                (int(float(r["n_lead"])), int(float(r["n_phonon"]))))
    for jw in ("tree_order", "energy_order"):
        for method in PANEL_C_METHODS:
            missing = set(EXPECTED_N_C.values()) - grid_c.get((jw, method), set())
            if missing:
                fail(f"panel (c) {jw} {method}: missing points {sorted(missing)}")

    # repeat count spot check
    rep_counts = defaultdict(int)
    for r in ok:
        if is_baseline(r) and float(r["ud_ev"]) == 0.0 and r["method"] == "ttno_with_env":
            rep_counts[int(float(r["n_total_sites"]))] += 1
    if any(v != 3 for v in rep_counts.values()):
        fail(f"repeat counts not all 3 for baseline U=0 ttno: {dict(rep_counts)}")
    else:
        info("baseline U=0 ttno: 3 repeats at every N")

    # 7. informational exponents (repeat medians, like the plotter)
    ts = defaultdict(lambda: defaultdict(list))
    for r in ok:
        if is_baseline(r) and float(r["ud_ev"]) in PANEL_AB_U:
            ts[(float(r["ud_ev"]), r["method"])][int(float(r["n_total_sites"]))].append(
                float(r["time_total_sec"]))
    for ud in sorted(PANEL_AB_U):
        for method in METHODS:
            med = sorted((n, float(np.median(v))) for n, v in ts[(ud, method)].items())
            if len(med) >= 4:
                alpha, window = largest_four_alpha(
                    np.array([p[0] for p in med]), np.array([p[1] for p in med]))
                info(f"U={ud} {method}: largest-4 alpha = {alpha:.3f} "
                     f"(window {window[0]}-{window[1]})")

    ts_c = defaultdict(lambda: defaultdict(list))
    for r in ok:
        if r["tree_topology"] == "bridge_centered" and layout_of(r) == PANEL_C_LAYOUT:
            ts_c[(jw_of(r), r["method"])][int(float(r["n_total_sites"]))].append(
                float(r["time_total_sec"]))
    for jw in ("tree_order", "energy_order"):
        for method in PANEL_C_METHODS:
            med = sorted((n, float(np.median(v))) for n, v in ts_c[(jw, method)].items())
            if len(med) >= 4:
                alpha, window = largest_four_alpha(
                    np.array([p[0] for p in med]), np.array([p[1] for p in med]))
                info(f"panel (c) {jw} {method}: largest-4 alpha = {alpha:.3f} "
                     f"(window {window[0]}-{window[1]})")

    print("\n".join(INFOS))
    if FAILS:
        print("\nHARD FAILURES:")
        print("\n".join("  - " + f for f in FAILS))
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
