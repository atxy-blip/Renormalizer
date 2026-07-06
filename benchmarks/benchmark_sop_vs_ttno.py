#!/usr/bin/env python3
"""Benchmark flat SOP application against compressed TTNO application.

The molecular-junction cases are small, parameterized benchmark variants of the
paper script ``../ttns-test/junction_zt_hubbard.py``.  The script itself runs
argument parsing, logging, TTNO construction, TTNS expansion, and time evolution
at import time, so the benchmark reuses its operator/tree construction pattern
instead of importing it as a module.
"""

import argparse
import csv
import gc
import json
import math
import sys
import time
import tracemalloc
from pathlib import Path
from statistics import median
from typing import Dict, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from renormalizer import BasisDummy, BasisHalfSpin, BasisSHO, Op, Quantity
from renormalizer.mps.backend import np
from renormalizer.sbm import SpectralDensityFunction
from renormalizer.tn import BasisTree, SOPBaselineOperator, TTNO, TTNS, TreeNodeBasis

import numpy as onp


RNG_SEED = 202407
JUNCTION_ZT_REFERENCE = "../ttns-test/junction_zt_hubbard.py"
RESULT_DIR = Path(__file__).resolve().parent / "results"
CSV_FIELDS = [
    "case",
    "n_lead",
    "n_phonon",
    "n_tfd_modes",
    "n_sites",
    "local_dim_summary",
    "sop_n_terms",
    "sop_nontrivial_local_ops",
    "ttno_max_bond_dim",
    "ttno_total_tensor_elements",
    "sop_estimated_storage",
    "ttno_estimated_storage",
    "sop_build_time_median",
    "ttno_build_time_median",
    "sop_apply_time_median",
    "ttno_apply_time_median",
    "sop_expectation_time_median",
    "ttno_expectation_time_median",
    "sop_apply_speedup",
    "ttno_storage_compression",
    "relative_apply_error",
    "expectation_error",
    "peak_memory_sop",
    "peak_memory_ttno",
    "status",
    "size",
    "rank",
    "current_relative_apply_error",
]


def _binary_or_dummy(basis_list, label):
    if len(basis_list) == 0:
        return TreeNodeBasis([BasisDummy((label, "empty"))])
    if len(basis_list) == 1:
        return TreeNodeBasis([basis_list[0]])
    return BasisTree.binary_mctdh(basis_list, dummy_label=label).root


def build_hubbard_junction_case(
    n_lead: int,
    n_phonon: int,
    *,
    ed: float = 0.0,
    ud: float = 0.0,
    bias: float = 0.1,
    alpha: float = 0.2,
    lam: float = 0.248,
    omegac: float = 500.0,
    use_e_ph: bool = True,
    initial_occupied: bool = False,
    max_phonon_basis: int = 4,
):
    """Build the paper-script Hubbard junction operator/tree at small sizes.

    ``n_lead`` matches ``--nemode`` in ``../ttns-test/junction_zt_hubbard.py``:
    each value creates left/right and spin-up/spin-down electrode modes, so the
    number of lead sites is ``4 * n_lead``.  The symbolic Hamiltonian, current
    operators, Jordan-Wigner ``Z`` strings, bridge placement, and tree layout
    follow that script.  The only benchmark-specific guard is a cap on SHO local
    basis size so default runs stay small enough for repeated timings.
    """

    n_e_mode = n_lead
    omega_c = Quantity(omegac, "cm-1").as_au()
    reorganization_energy = Quantity(lam, "eV").as_au()
    sdf = SpectralDensityFunction(reorganization_energy / omega_c / 2, omega_c)
    w, c2 = sdf.Wang1(n_phonon)
    c = np.sqrt(c2) if use_e_ph else np.zeros_like(c2)

    reno = sdf.reno(w[-1])
    beta_e = Quantity(1, "eV").as_au() * reno
    alpha_e = Quantity(alpha, "eV").as_au() * reno
    mu_l = Quantity(bias * reno / 2, "eV").as_au()
    mu_r = Quantity(-bias * reno / 2, "eV").as_au()
    u_d = Quantity(ud, "eV").as_au()
    e_d = Quantity(ed, "eV").as_au()

    e_k = np.arange(1, n_e_mode + 1) / (n_e_mode + 1) * 4 * beta_e - 2 * beta_e
    rho_e = 1 / (e_k[1] - e_k[0]) if n_e_mode > 1 else 1 / (4 * beta_e)
    e_k_l = e_k - mu_l
    e_k_r = e_k - mu_r
    mode_with_e = [
        (name, e) for i, e in enumerate(e_k_l) for name in (f"L_{i}", f"L^{i}")
    ] + [(name, e) for i, e in enumerate(e_k_r) for name in (f"R_{i}", f"R^{i}")]
    mode_with_e.sort(key=lambda item: item[1])

    basis = []
    first_positive = True
    for mode, energy in mode_with_e:
        if energy > 0 and first_positive:
            first_positive = False
            basis.append(BasisHalfSpin("s^"))
            basis.append(BasisHalfSpin("s_"))
        basis.append(BasisHalfSpin(mode))
    if first_positive:
        basis.append(BasisHalfSpin("s^"))
        basis.append(BasisHalfSpin("s_"))

    dofs = [b.dofs[0] for b in basis]
    su_idx = dofs.index("s^")
    spin_to_idx = {"^": su_idx, "_": su_idx + 1}

    basis_tree_l_root = _binary_or_dummy(basis[:su_idx], "EL-dummy")
    basis_tree_r_root = _binary_or_dummy(basis[su_idx + 2 :], "ER-dummy")

    ham_terms: List[Op] = []
    i_l_terms: List[Op] = []
    i_r_terms: List[Op] = []
    for mode, energy in mode_with_e:
        if mode[0] == "L":
            mu = mu_l
            i_terms = i_l_terms
        else:
            mu = mu_r
            i_terms = i_r_terms
        s_idx = spin_to_idx[mode[1]]
        ham_terms.append(Op("+ -", mode, energy + mu))

        v2 = (
            alpha_e**2
            / beta_e**2
            * np.sqrt(max(float(4 * beta_e**2 - (energy + mu) ** 2), 0.0))
            / 2
            / np.pi
            / rho_e
        )
        coupling = np.sqrt(v2)
        idx = dofs.index(mode)
        z_idx = list(range(idx + 1, s_idx)) if idx < s_idx else list(range(s_idx + 1, idx))
        z_dofs = [dofs[i] for i in z_idx]
        ele_dof = "s" + mode[1]
        op1 = Op("+ " + "Z " * len(z_idx) + "-", [mode] + z_dofs + [ele_dof], coupling)
        op2 = Op("- " + "Z " * len(z_idx) + "+", [mode] + z_dofs + [ele_dof], coupling)
        ham_terms.extend([op1, op2])
        i_terms.extend(op2 - op1)

    ham_terms.extend([
        Op("+ -", "s^", qn=[0, 0], factor=e_d),
        Op("+ -", "s_", qn=[0, 0], factor=e_d),
    ])
    ham_terms.append(Op("+ -", "s^", qn=[0, 0]) * Op("+ -", "s_", qn=[0, 0], factor=u_d))

    for imode in range(n_phonon):
        dof = f"v_{imode}"
        ham_terms.extend([
            Op("p^2", dof, factor=0.5, qn=0),
            Op("x^2", dof, factor=0.5 * w[imode] ** 2, qn=0),
        ])
        if initial_occupied:
            ham_terms.extend([
                Op("x", dof, factor=-2 * c[imode], qn=0),
                Op("I", dof, factor=2 * c[imode] ** 2 / w[imode] ** 2, qn=0),
            ])

    for imode in range(n_phonon):
        sys_op = Op("+ -", "s^", qn=[0, 0]) + Op("+ -", "s_", qn=[0, 0])
        ph_op = Op("x", f"v_{imode}", factor=2.0 * c[imode], qn=[0])
        if initial_occupied:
            ph_op += Op("I", f"v_{imode}", factor=-4.0 * c[imode] ** 2 / w[imode] ** 2, qn=[0])
        ham_terms.extend(sys_op * ph_op)

    nbas = np.max([16 * c2 / w**3, np.ones(n_phonon) * 4], axis=0)
    nbas = np.minimum(np.round(nbas).astype(int), max_phonon_basis)
    basis_list_phonon = [
        BasisSHO(f"v_{imode}", w[imode], int(nbas[imode])) for imode in range(n_phonon)
    ]
    basis_tree_phonon_root = _binary_or_dummy(basis_list_phonon, "phonon-dummy")

    node1 = TreeNodeBasis([basis[su_idx]])
    node1.add_child([basis_tree_l_root, basis_tree_r_root])
    node2 = TreeNodeBasis([basis[su_idx + 1]])
    node2.add_child([node1, basis_tree_phonon_root])
    tree = BasisTree(node2)

    condition = {dofs[i]: 1 for i in range(su_idx + 2, len(dofs))}
    condition["s^"] = 0 if initial_occupied else 1
    condition["s_"] = 0 if initial_occupied else 1
    psi = TTNS(tree, condition=condition)
    return tree, ham_terms, i_l_terms + i_r_terms, psi


def build_junction_case(n_lead: int, n_phonon: int, **kwargs):
    """Backward-compatible alias for the Hubbard junction benchmark builder."""

    return build_hubbard_junction_case(n_lead, n_phonon, **kwargs)

def build_shared_structure_case(size: int, rank: int):
    """Artificial flattened low-rank A/B coupling stress test."""

    basis_a = [BasisHalfSpin(("A", i)) for i in range(size)]
    basis_b = [BasisHalfSpin(("B", i)) for i in range(size)]
    root = TreeNodeBasis([BasisDummy("shared-root")])
    root.add_child([BasisTree.binary_mctdh(basis_a, dummy_label="A-dummy").root])
    root.add_child([BasisTree.binary_mctdh(basis_b, dummy_label="B-dummy").root])
    tree = BasisTree(root)

    rng = onp.random.default_rng(RNG_SEED + 17 * rank + size)
    x = rng.normal(size=(rank, size))
    y = rng.normal(size=(rank, size))
    terms = []
    for i in range(size):
        for j in range(size):
            vij = float(onp.dot(x[:, i], y[:, j]) / max(rank, 1) / max(size, 1))
            terms.append(Op("X X", [("A", i), ("B", j)], factor=vij))
    psi = TTNS(tree, condition={})
    return tree, terms, [], psi


def _ttno_elements(ttno: TTNO) -> int:
    return int(sum(node.tensor.size for node in ttno))


def _local_dim_summary(tree: BasisTree) -> str:
    counts = {}
    for basis in tree.basis_list:
        counts[basis.nbas] = counts.get(basis.nbas, 0) + 1
    return json.dumps(sorted(counts.items()))


def _time_repeats(fn, repeats: int) -> Tuple[float, float, float]:
    timings = []
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - start)
    return float(median(timings)), float(min(timings)), float(max(timings))


def _time_build(factory, repeats: int):
    built = None
    timings = []
    for _ in range(repeats):
        gc.collect()
        start = time.perf_counter()
        built = factory()
        timings.append(time.perf_counter() - start)
    return built, float(median(timings)), float(min(timings)), float(max(timings))


def _peak_memory(fn) -> int:
    gc.collect()
    tracemalloc.start()
    fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return int(peak)


def _relative_state_error(lhs, rhs, tree: BasisTree) -> float:
    physical_order = [b for b in tree.basis_list if not isinstance(b, BasisDummy)]
    physical_dim = int(onp.prod([b.nbas for b in physical_order])) if physical_order else 1
    if physical_dim <= 4_000_000:
        lhs_vec = lhs.todense(physical_order).ravel()
        rhs_vec = rhs.todense(physical_order).ravel()
        denom = np.linalg.norm(rhs_vec)
        diff = np.linalg.norm(lhs_vec - rhs_vec)
        return float(diff / denom) if denom != 0 else float(diff)

    diff = lhs.add(rhs.scale(-1))
    denom = rhs.norm
    if denom == 0:
        return float(diff.norm)
    return float(diff.norm / denom)


def _benchmark_success_row(case: str, n_lead: int, n_phonon: int, size: int, rank: int, repeats: int) -> Dict:
    if case == "shared-structure":
        tree, terms, current_terms, psi = build_shared_structure_case(size, rank)
        n_lead = 0
        n_phonon = 0
        n_tfd_modes = 0
    else:
        tree, terms, current_terms, psi = build_hubbard_junction_case(n_lead, n_phonon)
        n_tfd_modes = 0

    sop, sop_build, _, _ = _time_build(lambda: SOPBaselineOperator.from_symbolic_terms(terms, tree), repeats)
    ttno, ttno_build, _, _ = _time_build(lambda: TTNO(tree, terms), repeats)

    # Warm-up outside timing. This absorbs opt_einsum path planning and local cache fills.
    sop.apply_to_ttns(psi)
    ttno.apply(psi)
    sop.expectation(psi)
    psi.expectation(ttno)

    sop_apply, _, _ = _time_repeats(lambda: sop.apply_to_ttns(psi), repeats)
    ttno_apply, _, _ = _time_repeats(lambda: ttno.apply(psi), repeats)
    sop_exp, _, _ = _time_repeats(lambda: sop.expectation(psi), repeats)
    ttno_exp, _, _ = _time_repeats(lambda: psi.expectation(ttno), repeats)

    sop_psi = sop.apply_to_ttns(psi)
    ttno_psi = ttno.apply(psi)
    rel_err = _relative_state_error(sop_psi, ttno_psi, tree)
    sop_expect = sop.expectation(psi)
    ttno_expect = psi.expectation(ttno)
    exp_err = float(abs(sop_expect - ttno_expect))

    current_rel_err = math.nan
    if current_terms:
        current_sop = SOPBaselineOperator.from_symbolic_terms(current_terms, tree)
        current_ttno = TTNO(tree, current_terms)
        current_rel_err = _relative_state_error(current_sop.apply_to_ttns(psi), current_ttno.apply(psi), tree)

    peak_sop = max(
        _peak_memory(lambda: SOPBaselineOperator.from_symbolic_terms(terms, tree)),
        _peak_memory(lambda: sop.apply_to_ttns(psi)),
        _peak_memory(lambda: sop.expectation(psi)),
    )
    peak_ttno = max(
        _peak_memory(lambda: TTNO(tree, terms)),
        _peak_memory(lambda: ttno.apply(psi)),
        _peak_memory(lambda: psi.expectation(ttno)),
    )

    ttno_storage = _ttno_elements(ttno)
    sop_storage = sop.estimate_storage()
    return {
        "case": case,
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_tfd_modes": n_tfd_modes,
        "n_sites": len([b for b in tree.basis_list if not isinstance(b, BasisDummy)]),
        "local_dim_summary": _local_dim_summary(tree),
        "sop_n_terms": sop.n_terms,
        "sop_nontrivial_local_ops": sop.count_nontrivial_local_ops(),
        "ttno_max_bond_dim": max(ttno.bond_dims),
        "ttno_total_tensor_elements": ttno_storage,
        "sop_estimated_storage": sop_storage,
        "ttno_estimated_storage": ttno_storage,
        "sop_build_time_median": sop_build,
        "ttno_build_time_median": ttno_build,
        "sop_apply_time_median": sop_apply,
        "ttno_apply_time_median": ttno_apply,
        "sop_expectation_time_median": sop_exp,
        "ttno_expectation_time_median": ttno_exp,
        "sop_apply_speedup": sop_apply / ttno_apply if ttno_apply else math.inf,
        "ttno_storage_compression": sop_storage / ttno_storage if ttno_storage else math.inf,
        "relative_apply_error": rel_err,
        "expectation_error": exp_err,
        "peak_memory_sop": peak_sop,
        "peak_memory_ttno": peak_ttno,
        "status": "ok",
        "size": size,
        "rank": rank,
        "current_relative_apply_error": current_rel_err,
    }


def run_one(case: str, n_lead: int, n_phonon: int, size: int, rank: int, repeats: int) -> Dict:
    try:
        return _benchmark_success_row(case, n_lead, n_phonon, size, rank, repeats)
    except Exception as exc:
        row = {field: math.nan for field in CSV_FIELDS}
        row.update({
            "case": case,
            "n_lead": n_lead,
            "n_phonon": n_phonon,
            "size": size,
            "rank": rank,
            "status": f"error: {type(exc).__name__}: {exc}",
        })
        return row


def write_summary(rows: List[Dict], path: Path):
    lines = [
        "# SOP vs TTNO Summary",
        "",
        f"Junction benchmark source pattern: `{JUNCTION_ZT_REFERENCE}`.",
        "",
        "The SOP baseline represents an ML-MCTDH-style operator layer: the symbolic Hamiltonian remains a flat sum of product terms and each product term is applied independently on the same TTNS tree and local basis. It is not a full ML-MCTDH propagator.",
        "",
        "TTNO can be more efficient because the operator is also represented as a tree tensor network. Shared identity strings, common subtrees, and repeated bridge/lead/phonon structure can be reused through operator bonds instead of being visited once per flattened SOP term.",
        "",
        "Small systems may favor SOP because TTNO construction and contraction overheads are visible. Interpret the table as scaling and crossover data, not as a universal speed claim.",
        "",
        "The lead and phonon cases isolate basis-size growth in the Hubbard junction construction. The shared-structure case isolates operator-count growth with an artificial low-rank product-operator family.",
        "",
        "| case | n_lead | n_phonon | terms | ttno max bond | sop apply (s) | ttno apply (s) | speedup | rel err | status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        def fmt(key, fmtstr):
            try:
                val = float(row[key])
                if math.isnan(val):
                    return "nan"
                return format(val, fmtstr)
            except Exception:
                return str(row.get(key, ""))
        lines.append(
            f"| {row['case']} | {row['n_lead']} | {row['n_phonon']} | {row['sop_n_terms']} | "
            f"{row['ttno_max_bond_dim']} | {fmt('sop_apply_time_median', '.6g')} | "
            f"{fmt('ttno_apply_time_median', '.6g')} | {fmt('sop_apply_speedup', '.3g')} | "
            f"{fmt('relative_apply_error', '.3e')} | {row['status']} |"
        )
    path.write_text("\n".join(lines) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["lead", "phonon", "shared-structure"], default="lead")
    parser.add_argument("--lead", type=int, default=4)
    parser.add_argument("--lead-list", nargs="+", type=int)
    parser.add_argument("--phonon", type=int, default=2)
    parser.add_argument("--phonon-list", nargs="+", type=int)
    parser.add_argument("--size", type=int, default=8)
    parser.add_argument("--size-list", nargs="+", type=int)
    parser.add_argument("--rank", type=int, default=2)
    parser.add_argument("--rank-list", nargs="+", type=int)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, default=RESULT_DIR / "sop_vs_ttno_results.csv")
    return parser.parse_args()


def _rows_for_args(args) -> List[Dict]:
    rows = []
    if args.case == "lead":
        for n_lead in args.lead_list or [1, 2, 4, 8]:
            rows.append(run_one("lead", n_lead, args.phonon, args.size, args.rank, args.repeats))
    elif args.case == "phonon":
        for n_phonon in args.phonon_list or [1, 2, 4, 8]:
            rows.append(run_one("phonon", args.lead, n_phonon, args.size, args.rank, args.repeats))
    else:
        for rank in args.rank_list or [args.rank]:
            for size in args.size_list or [4, 8, 16]:
                rows.append(run_one("shared-structure", 0, 0, size, rank, args.repeats))
    return rows


def main():
    args = parse_args()
    onp.random.seed(RNG_SEED)
    np.random.seed(RNG_SEED)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows = _rows_for_args(args)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_summary(rows, RESULT_DIR / "sop_vs_ttno_summary.md")
    print(f"Wrote {args.output}")
    print(f"Wrote {RESULT_DIR / 'sop_vs_ttno_summary.md'}")


if __name__ == "__main__":
    main()
