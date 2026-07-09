#!/usr/bin/env python3
"""Adaptive CPU benchmark for SOP/TTNO environment paths.

The measured quantity is one-site local effective Hamiltonian action at the
TTNS root.  This is intentional: contraction environments are local-update
objects, while full-state ``H|psi>`` is kept for small correctness checks only.
"""

import argparse
import csv
import gc
import json
import math
import os
import signal
import sys
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# This benchmark is intentionally CPU-only.  These defaults must be in place
# before importing renormalizer so backend/thread selection is deterministic.
os.environ.setdefault("RENO_GPU", "cpu")
os.environ.setdefault("RENO_NUM_THREADS", "1")

from renormalizer import BasisDummy, BasisHalfSpin, BasisSHO, Op, Quantity
from renormalizer.mps.backend import np
from renormalizer.mps.oe_contract_wrap import oe_contract
from renormalizer.sbm import SpectralDensityFunction
from renormalizer.tn import BasisTree, SOPBaselineOperator, TTNO, TTNS, TreeNodeBasis
from renormalizer.tn.hop_expr import hop_expr1
from renormalizer.tn.tree import TTNEnviron

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as onp


RNG_SEED = 202407
RESULT_DIR = Path(__file__).resolve().parent / "results"
METHODS = ("sop_no_env", "sop_with_env", "ttno_with_env")
RAW_FIELDS = [
    "case_name",
    "scaling_path",
    "n_lead",
    "n_phonon",
    "n_fermion_sites",
    "n_boson_sites",
    "n_total_sites",
    "n_sop_terms",
    "ttno_max_bond",
    "ttno_mean_bond",
    "state_max_bond",
    "local_basis_summary",
    "active_node_idx",
    "quantity",
    "method",
    "repeat_id",
    "time_env_build_sec",
    "time_expr_build_sec",
    "time_apply_sec",
    "time_total_sec",
    "memory_peak_mb",
    "relative_error_vs_ttno",
    "backend",
    "num_threads",
    "git_commit",
    "status",
    "overhead_region",
]
FIT_FIELDS = [
    "method",
    "scaling_path",
    "x_axis",
    "fit_window",
    "alpha",
    "intercept_logC",
    "r2",
    "n_points_used",
    "points_excluded",
    "alpha_delta_vs_large",
    "stable_vs_large",
]


class BenchmarkTimeout(TimeoutError):
    pass


@contextmanager
def time_limit(seconds: int):
    if seconds <= 0:
        yield
        return

    def handler(_signum, _frame):
        raise BenchmarkTimeout(f"exceeded {seconds} s")

    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


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
    """Build the Hubbard junction tree, including the n_phonon=0 lead-only case."""

    n_e_mode = n_lead
    omega_c = Quantity(omegac, "cm-1").as_au()
    reorganization_energy = Quantity(lam, "eV").as_au()
    sdf = SpectralDensityFunction(reorganization_energy / omega_c / 2, omega_c)
    if n_phonon > 0:
        w, c2 = sdf.Wang1(n_phonon)
        c = np.sqrt(c2) if use_e_ph else np.zeros_like(c2)
        reno = sdf.reno(w[-1])
    else:
        w = np.array([])
        c2 = np.array([])
        c = np.array([])
        reno = 1.0

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
    for mode, energy in mode_with_e:
        mu = mu_l if mode[0] == "L" else mu_r
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
        ham_terms.append(Op("+ " + "Z " * len(z_idx) + "-", [mode] + z_dofs + [ele_dof], coupling))
        ham_terms.append(Op("- " + "Z " * len(z_idx) + "+", [mode] + z_dofs + [ele_dof], coupling))

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

    if n_phonon > 0:
        nbas = np.max([16 * c2 / w**3, np.ones(n_phonon) * 4], axis=0)
        nbas = np.minimum(np.round(nbas).astype(int), max_phonon_basis)
        basis_list_phonon = [
            BasisSHO(f"v_{imode}", w[imode], int(nbas[imode])) for imode in range(n_phonon)
        ]
    else:
        basis_list_phonon = []
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
    return tree, ham_terms, psi


def _apply_matrix_on_axis(tensor, mat, axis):
    res = np.tensordot(mat, tensor, axes=(1, axis))
    return np.moveaxis(res, 0, axis)


class SOPOneSiteEffective:
    """One-site SOP local effective action with optional branch environment cache."""

    def __init__(self, sop: SOPBaselineOperator, ttns: TTNS, active_node=None):
        self.sop = sop
        self.ttns = ttns
        self.active_node = active_node or ttns.root
        self.active_idx = ttns.node_idx[self.active_node]
        self._env_cache: Dict[Tuple[int, Tuple], np.ndarray] = {}

    def branch_signature(self, node, term) -> Tuple:
        items = []
        for snode in self._subtree_postorder(node):
            idx = self.ttns.node_idx[snode]
            op = term.local_ops.get(idx)
            if op is not None:
                items.append((idx, op.to_tuple()))
        return tuple(items)

    def build_env_cache(self):
        for term in self.sop.terms:
            for child in self.active_node.children:
                key = (self.ttns.node_idx[child], self.branch_signature(child, term))
                if key not in self._env_cache:
                    self._env_cache[key] = self._contract_subtree(child, term, use_cache=True)

    def apply(self, use_env: bool):
        result = np.zeros_like(self.active_node.tensor)
        for term in self.sop.terms:
            result = result + self._apply_term(term, use_env=use_env)
        return result

    def _subtree_postorder(self, node):
        nodes = []
        for child in node.children:
            nodes.extend(self._subtree_postorder(child))
        nodes.append(node)
        return nodes

    def _branch_env(self, child, term, use_cache: bool):
        if not use_cache:
            return self._contract_subtree(child, term, use_cache=False)
        key = (self.ttns.node_idx[child], self.branch_signature(child, term))
        if key not in self._env_cache:
            self._env_cache[key] = self._contract_subtree(child, term, use_cache=True)
        return self._env_cache[key]

    def _contract_subtree(self, node, term, use_cache: bool):
        node_idx = self.ttns.node_idx[node]
        ket = node.tensor
        factors = self.sop._local_matrix_factors(node_idx, term.local_ops.get(node_idx))
        physical_axis0 = len(node.children)
        for ibasis, mat in enumerate(factors):
            if mat is not None:
                ket = _apply_matrix_on_axis(ket, mat, physical_axis0 + ibasis)

        args = []
        bra_indices = []
        ket_indices = []
        for child in node.children:
            env = self._branch_env(child, term, use_cache=use_cache)
            child_idx = self.ttns.node_idx[child]
            bra_child = ("sop_bra_child", child_idx)
            ket_child = ("sop_ket_child", child_idx)
            args.extend([env, [bra_child, ket_child]])
            bra_indices.append(bra_child)
            ket_indices.append(ket_child)

        for iphys in range(len(node.tensor.shape) - len(node.children) - 1):
            phys = ("sop_phys", node_idx, iphys)
            bra_indices.append(phys)
            ket_indices.append(phys)

        bra_parent = ("sop_bra_parent", node_idx)
        ket_parent = ("sop_ket_parent", node_idx)
        bra_indices.append(bra_parent)
        ket_indices.append(ket_parent)
        args.extend([node.tensor.conj(), bra_indices, ket, ket_indices, [bra_parent, ket_parent]])
        return oe_contract(*args)

    def _apply_term(self, term, use_env: bool):
        tensor = self.active_node.tensor
        factors = self.sop._local_matrix_factors(self.active_idx, term.local_ops.get(self.active_idx))
        physical_axis0 = len(self.active_node.children)
        for ibasis, mat in enumerate(factors):
            if mat is not None:
                tensor = _apply_matrix_on_axis(tensor, mat, physical_axis0 + ibasis)
        tensor = tensor * term.coeff

        args = [tensor]
        tensor_indices = []
        output_indices = []
        for child in self.active_node.children:
            env = self._branch_env(child, term, use_cache=use_env)
            child_idx = self.ttns.node_idx[child]
            bra_child = ("sop_active_bra_child", child_idx)
            ket_child = ("sop_active_ket_child", child_idx)
            args.extend([env, [bra_child, ket_child]])
            tensor_indices.append(ket_child)
            output_indices.append(bra_child)

        for iphys in range(len(tensor.shape) - len(self.active_node.children) - 1):
            phys = ("sop_active_phys", self.active_idx, iphys)
            tensor_indices.append(phys)
            output_indices.append(phys)

        parent = ("sop_active_parent", self.active_idx)
        tensor_indices.append(parent)
        output_indices.append(parent)
        args.insert(1, tensor_indices)
        args.append(output_indices)
        return oe_contract(*args)


def _time_and_memory(fn, timeout_sec: int):
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    try:
        with time_limit(timeout_sec):
            value = fn()
        status = "ok"
    except BenchmarkTimeout as exc:
        value = None
        status = f"timeout: {exc}"
    except MemoryError as exc:
        value = None
        status = f"memory_error: {exc}"
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return value, elapsed, peak / 1024 / 1024, status


def _ttno_one_site_action(ttns, ttno, active_node, timeout_sec: int):
    ttne, env_time, env_mem, env_status = _time_and_memory(lambda: TTNEnviron(ttns, ttno), timeout_sec)
    if env_status != "ok":
        return None, env_time, 0.0, 0.0, env_mem, env_status
    expr, expr_time, expr_mem, expr_status = _time_and_memory(lambda: hop_expr1(active_node, ttns, ttno, ttne), timeout_sec)
    if expr_status != "ok":
        return None, env_time, expr_time, 0.0, max(env_mem, expr_mem), expr_status
    action, apply_time, apply_mem, apply_status = _time_and_memory(lambda: expr(active_node.tensor), timeout_sec)
    return action, env_time, expr_time, apply_time, max(env_mem, expr_mem, apply_mem), apply_status


def _sop_one_site_action(sop, ttns, active_node, method: str, timeout_sec: int):
    applier = SOPOneSiteEffective(sop, ttns, active_node)
    env_time = 0.0
    env_mem = 0.0
    if method == "sop_with_env":
        _, env_time, env_mem, env_status = _time_and_memory(applier.build_env_cache, timeout_sec)
        if env_status != "ok":
            return None, env_time, 0.0, 0.0, env_mem, env_status
    action, apply_time, apply_mem, apply_status = _time_and_memory(
        lambda: applier.apply(use_env=(method == "sop_with_env")), timeout_sec
    )
    return action, env_time, 0.0, apply_time, max(env_mem, apply_mem), apply_status


def _relative_error(action, reference):
    if action is None or reference is None:
        return math.nan
    action = np.asarray(action)
    reference = np.asarray(reference)
    denom = np.linalg.norm(reference.ravel())
    diff = np.linalg.norm((action - reference).ravel())
    return float(diff / denom) if denom != 0 else float(diff)


def _is_resource_failure(status) -> bool:
    status = str(status)
    return (
        status.startswith("timeout:")
        or status.startswith("memory_error:")
        or status.startswith("memory_limit_exceeded:")
    )


def _git_commit():
    import subprocess

    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _local_dim_summary(tree):
    counts = {}
    for basis in tree.basis_list:
        name = basis.__class__.__name__
        key = f"{name}:{basis.nbas}"
        counts[key] = counts.get(key, 0) + 1
    return json.dumps(counts, sort_keys=True)


def _point_metadata(path_name, n_lead, n_phonon, tree, psi, sop, ttno, active_node, git_commit):
    n_fermion_sites = 4 * n_lead + 2
    n_boson_sites = n_phonon
    return {
        "case_name": "hubbard_junction",
        "scaling_path": path_name,
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_fermion_sites": n_fermion_sites,
        "n_boson_sites": n_boson_sites,
        "n_total_sites": n_fermion_sites + n_boson_sites,
        "n_sop_terms": sop.n_terms,
        "ttno_max_bond": max(ttno.bond_dims),
        "ttno_mean_bond": float(onp.mean(ttno.bond_dims)),
        "state_max_bond": max(psi.bond_dims),
        "local_basis_summary": _local_dim_summary(tree),
        "active_node_idx": tree.node_idx[tree.root],
        "quantity": "local_effective_1site_apply",
        "backend": "cpu",
        "num_threads": os.environ.get("RENO_NUM_THREADS", ""),
        "git_commit": git_commit,
    }


def _method_row(metadata, method, repeat_id, env_t, expr_t, apply_t, mem_mb, rel_err, status):
    return {
        **metadata,
        "method": method,
        "repeat_id": repeat_id,
        "time_env_build_sec": env_t,
        "time_expr_build_sec": expr_t,
        "time_apply_sec": apply_t,
        "time_total_sec": env_t + expr_t + apply_t,
        "memory_peak_mb": mem_mb,
        "relative_error_vs_ttno": rel_err,
        "status": status,
        "overhead_region": "",
    }


def _run_point(path_name, n_lead, n_phonon, repeat_id, args, git_commit, skip_methods=frozenset()):
    tree, terms, psi = build_hubbard_junction_case(n_lead, n_phonon, max_phonon_basis=args.max_phonon_basis)
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    active_node = psi.root
    metadata = _point_metadata(path_name, n_lead, n_phonon, tree, psi, sop, ttno, active_node, git_commit)

    rows = []
    if "ttno_with_env" in skip_methods:
        ref = None
        rows.append(_method_row(
            metadata, "ttno_with_env", repeat_id, 0.0, 0.0, 0.0, 0.0, math.nan,
            "skipped_after_previous_timeout_or_memory",
        ))
    else:
        ref, env_t, expr_t, apply_t, mem_mb, status = _ttno_one_site_action(psi, ttno, active_node, args.timeout_sec)
        if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
            status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"
        rows.append(_method_row(
            metadata, "ttno_with_env", repeat_id, env_t, expr_t, apply_t, mem_mb,
            0.0 if status == "ok" else math.nan, status,
        ))

    for method in ("sop_no_env", "sop_with_env"):
        if method in skip_methods:
            rows.append(_method_row(
                metadata, method, repeat_id, 0.0, 0.0, 0.0, 0.0, math.nan,
                "skipped_after_previous_timeout_or_memory",
            ))
            continue
        action, env_t, expr_t, apply_t, mem_mb, status = _sop_one_site_action(
            sop, psi, active_node, method, args.timeout_sec
        )
        if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
            status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"
        rows.append(_method_row(
            metadata, method, repeat_id, env_t, expr_t, apply_t, mem_mb,
            _relative_error(action, ref) if status == "ok" else math.nan, status,
        ))
    return rows


def _parse_int_list(text: str) -> List[int]:
    return [int(x) for x in text.replace(",", " ").split() if x]


def _parse_pairs(text: str) -> List[Tuple[int, int]]:
    pairs = []
    for item in text.replace(";", " ").split():
        left, right = item.split(":")
        pairs.append((int(left), int(right)))
    return pairs


def _scaling_points(args):
    paths = []
    if args.scaling_path in ("lead_only", "all"):
        leads = _parse_int_list(args.lead_values)
        paths.append(("lead_only", [(n, 0) for n in leads]))
    if args.scaling_path in ("balanced_lead_phonon", "all"):
        paths.append(("balanced_lead_phonon", _parse_pairs(args.balanced_pairs)))
    return paths


def _ok_rows(rows):
    return [r for r in rows if str(r["status"]).startswith("ok") and float(r["time_total_sec"]) > 0]


def _fit_one(rows, method, scaling_path, x_axis, fit_window, stability_tol):
    candidates = [
        r for r in _ok_rows(rows)
        if r["method"] == method and r["scaling_path"] == scaling_path and float(r[x_axis]) > 0
    ]
    candidates.sort(key=lambda r: float(r[x_axis]))
    if fit_window == "large_only" and len(candidates) >= 4:
        used = candidates[len(candidates) // 2 :]
    else:
        used = candidates
    excluded = [f"{r['n_lead']}:{r['n_phonon']}" for r in candidates if r not in used]
    if len(used) < 2:
        return {
            "method": method,
            "scaling_path": scaling_path,
            "x_axis": x_axis,
            "fit_window": fit_window,
            "alpha": math.nan,
            "intercept_logC": math.nan,
            "r2": math.nan,
            "n_points_used": len(used),
            "points_excluded": json.dumps(excluded),
            "alpha_delta_vs_large": math.nan,
            "stable_vs_large": "",
        }
    x = onp.log(onp.array([float(r[x_axis]) for r in used]))
    y = onp.log(onp.array([float(r["time_total_sec"]) for r in used]))
    alpha, intercept = onp.polyfit(x, y, 1)
    pred = alpha * x + intercept
    ss_res = float(onp.sum((y - pred) ** 2))
    ss_tot = float(onp.sum((y - onp.mean(y)) ** 2))
    r2 = 1.0 if ss_tot == 0 else 1 - ss_res / ss_tot
    return {
        "method": method,
        "scaling_path": scaling_path,
        "x_axis": x_axis,
        "fit_window": fit_window,
        "alpha": float(alpha),
        "intercept_logC": float(intercept),
        "r2": float(r2),
        "n_points_used": len(used),
        "points_excluded": json.dumps(excluded),
        "alpha_delta_vs_large": math.nan,
        "stable_vs_large": "",
    }


def compute_fits(rows, stability_tol: float):
    fits = []
    x_axes = ["n_total_sites", "n_sop_terms", "n_lead", "n_phonon"]
    paths = sorted({r["scaling_path"] for r in rows})
    for path in paths:
        for method in METHODS:
            for x_axis in x_axes:
                if x_axis == "n_phonon" and path == "lead_only":
                    continue
                all_fit = _fit_one(rows, method, path, x_axis, "all_ok", stability_tol)
                large_fit = _fit_one(rows, method, path, x_axis, "large_only", stability_tol)
                if not math.isnan(all_fit["alpha"]) and not math.isnan(large_fit["alpha"]):
                    delta = abs(all_fit["alpha"] - large_fit["alpha"])
                    all_fit["alpha_delta_vs_large"] = delta
                    large_fit["alpha_delta_vs_large"] = delta
                    has_distinct_large_window = large_fit["points_excluded"] != "[]"
                    stable = str(has_distinct_large_window and delta <= stability_tol)
                    all_fit["stable_vs_large"] = stable
                    large_fit["stable_vs_large"] = stable
                fits.extend([all_fit, large_fit])
    return fits


def mark_overhead_rows(rows):
    for path in sorted({r["scaling_path"] for r in rows}):
        ok = [r for r in _ok_rows(rows) if r["scaling_path"] == path]
        if not ok:
            continue
        threshold = onp.median([float(r["n_total_sites"]) for r in ok])
        for row in rows:
            if row["scaling_path"] == path:
                row["overhead_region"] = "small_overhead_candidate" if float(row["n_total_sites"]) < threshold else "fit_candidate"


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_plots(rows, output_prefix: Path):
    ok = _ok_rows(rows)
    if not ok:
        return
    for path in sorted({r["scaling_path"] for r in ok}):
        for x_axis in ("n_total_sites", "n_sop_terms"):
            fig, ax = plt.subplots(figsize=(6.5, 4.0))
            for method in METHODS:
                group = [r for r in ok if r["scaling_path"] == path and r["method"] == method]
                group.sort(key=lambda r: float(r[x_axis]))
                if not group:
                    continue
                ax.plot(
                    [float(r[x_axis]) for r in group],
                    [float(r["time_total_sec"]) for r in group],
                    marker="o",
                    label=method,
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_xlabel(x_axis)
            ax.set_ylabel("time_total_sec")
            ax.set_title(f"{path}: local effective action")
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(output_prefix.parent / f"{output_prefix.name}_{path}_time_vs_{x_axis}.png", dpi=180)
            plt.close(fig)

        diagnostics = [
            ("n_sop_terms", "SOP terms"),
            ("ttno_max_bond", "TTNO max bond"),
        ]
        fig, axes = plt.subplots(1, 3, figsize=(14, 4))
        point_rows = {}
        for r in ok:
            if r["scaling_path"] == path and r["method"] == "ttno_with_env":
                point_rows[(r["n_lead"], r["n_phonon"])] = r
        diag_rows = sorted(point_rows.values(), key=lambda r: float(r["n_total_sites"]))
        for ax, (y_axis, ylabel) in zip(axes[:2], diagnostics):
            ax.plot([float(r["n_total_sites"]) for r in diag_rows], [float(r[y_axis]) for r in diag_rows], marker="o")
            ax.set_xlabel("n_total_sites")
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.3)
        ax = axes[2]
        for method in METHODS:
            group = [r for r in ok if r["scaling_path"] == path and r["method"] == method]
            group.sort(key=lambda r: float(r["n_total_sites"]))
            if group:
                ax.plot(
                    [float(r["n_total_sites"]) for r in group],
                    [float(r["time_total_sec"]) / max(float(r["n_sop_terms"]), 1.0) for r in group],
                    marker="o",
                    label=method,
                )
        ax.set_xlabel("n_total_sites")
        ax.set_ylabel("time_total_sec / n_sop_terms")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_prefix.parent / f"{output_prefix.name}_{path}_diagnostics.png", dpi=180)
        plt.close(fig)


def run_benchmark(args):
    onp.random.seed(RNG_SEED)
    np.random.seed(RNG_SEED)
    git_commit = _git_commit()
    rows = []

    for path_name, initial_points in _scaling_points(args):
        points = list(initial_points)
        disabled_methods = set()
        extra_used = 0
        consecutive_hard_failures = 0
        idx = 0
        while idx < len(points):
            n_lead, n_phonon = points[idx]
            point_rows = []
            for repeat_id in range(args.repeats):
                try:
                    point_rows.extend(
                        _run_point(path_name, n_lead, n_phonon, repeat_id, args, git_commit, disabled_methods)
                    )
                except Exception as exc:
                    point_rows.append({
                        **{field: math.nan for field in RAW_FIELDS},
                        "case_name": "hubbard_junction",
                        "scaling_path": path_name,
                        "n_lead": n_lead,
                        "n_phonon": n_phonon,
                        "method": "point_setup",
                        "repeat_id": repeat_id,
                        "status": f"error: {type(exc).__name__}: {exc}",
                        "backend": "cpu",
                        "num_threads": os.environ.get("RENO_NUM_THREADS", ""),
                        "git_commit": git_commit,
                    })
            for row in point_rows:
                if row.get("method") in METHODS and _is_resource_failure(row.get("status")):
                    disabled_methods.add(row["method"])
            rows.extend(point_rows)
            ok_methods = {r["method"] for r in point_rows if str(r["status"]).startswith("ok")}
            if not ok_methods:
                consecutive_hard_failures += 1
            else:
                consecutive_hard_failures = 0
            if consecutive_hard_failures >= args.stop_after_consecutive_failures:
                break

            idx += 1
            if idx == len(points) and extra_used < args.max_extra_points:
                fits = compute_fits(rows, args.alpha_stability_tol)
                relevant = [
                    f for f in fits
                    if f["scaling_path"] == path_name
                    and f["x_axis"] == "n_total_sites"
                    and f["fit_window"] == "all_ok"
                    and f["stable_vs_large"] == "True"
                ]
                if len(relevant) < len(METHODS):
                    last_lead, last_phonon = points[-1]
                    if path_name == "lead_only":
                        points.append((last_lead * 2, 0))
                    else:
                        points.append((last_lead * 2, max(last_phonon * 2, 1)))
                    extra_used += 1

    mark_overhead_rows(rows)
    fits = compute_fits(rows, args.alpha_stability_tol)
    write_csv(args.output, rows, RAW_FIELDS)
    write_csv(args.fit_output, fits, FIT_FIELDS)
    save_plots(rows, args.output.with_suffix(""))
    return rows, fits


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scaling-path", choices=["lead_only", "balanced_lead_phonon", "all"], default="all")
    parser.add_argument("--lead-values", default="4 8 16 32 64 128")
    parser.add_argument("--balanced-pairs", default="4:1 8:2 16:4 32:8 64:16")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--memory-limit-mb", type=float, default=0.0)
    parser.add_argument("--max-extra-points", type=int, default=1)
    parser.add_argument("--stop-after-consecutive-failures", type=int, default=2)
    parser.add_argument("--alpha-stability-tol", type=float, default=0.25)
    parser.add_argument("--max-phonon-basis", type=int, default=4)
    parser.add_argument("--output", type=Path, default=RESULT_DIR / "adaptive_operator_env_raw.csv")
    parser.add_argument("--fit-output", type=Path, default=RESULT_DIR / "adaptive_operator_env_fits.csv")
    return parser.parse_args()


def main():
    args = parse_args()
    rows, fits = run_benchmark(args)
    print(f"Wrote {args.output} ({len(rows)} rows)")
    print(f"Wrote {args.fit_output} ({len(fits)} rows)")


if __name__ == "__main__":
    main()
