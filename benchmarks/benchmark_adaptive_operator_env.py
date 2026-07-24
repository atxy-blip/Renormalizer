#!/usr/bin/env python3
"""Adaptive CPU benchmark for SOP/TTNO environment paths.

The measured quantity is one-site local effective Hamiltonian action, either at
the TTNS root or over all TTNS nodes.  This is intentional: contraction
environments are local-update objects, while full-state ``H|psi>`` is kept for
small correctness checks only.
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
SOP_CACHE_NONE = "none"
SOP_CACHE_TERM = "term"
SOP_CACHE_SIGNATURE = "signature"

SOP_METHOD_CACHE_MODE = {
    "sop_no_env": SOP_CACHE_NONE,
    "sop_mctdh_like_state_env": SOP_CACHE_TERM,
    "sop_env_plus_operator_cache": SOP_CACHE_SIGNATURE,
    "sop_with_env": SOP_CACHE_SIGNATURE,
}

METHODS = (
    "sop_no_env",
    "sop_mctdh_like_state_env",
    "sop_env_plus_operator_cache",
    "ttno_with_env",
)
RAW_FIELDS = [
    "case_name",
    "scaling_path",
    "n_lead",
    "n_phonon",
    "n_fermion_sites",
    "n_boson_sites",
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
    "local_basis_summary",
    "active_node_idx",
    "quantity",
    "method",
    "repeat_id",
    "time_env_build_sec",
    "time_expr_build_sec",
    "time_term_loop_sec",
    "time_apply_sec",
    "time_total_sec",
    "n_env_cache_entries",
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


def _binary_or_dummy(basis_list, label, contract_primitive=False):
    if len(basis_list) == 0:
        return TreeNodeBasis([BasisDummy((label, "empty"))])
    if len(basis_list) == 1:
        return TreeNodeBasis([basis_list[0]])
    return BasisTree.binary_mctdh(
        basis_list,
        contract_primitive=contract_primitive,
        dummy_label=label,
    ).root


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
    force_phonon_basis: int = None,
    phonon_contract_primitive: bool = False,
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
        if force_phonon_basis is None:
            nbas = np.max([16 * c2 / w**3, np.ones(n_phonon) * 4], axis=0)
            nbas = np.minimum(np.round(nbas).astype(int), max_phonon_basis)
        else:
            nbas = np.ones(n_phonon, dtype=int) * int(force_phonon_basis)
        basis_list_phonon = [
            BasisSHO(f"v_{imode}", w[imode], int(nbas[imode])) for imode in range(n_phonon)
        ]
    else:
        basis_list_phonon = []
    basis_tree_phonon_root = _binary_or_dummy(
        basis_list_phonon,
        "phonon-dummy",
        contract_primitive=phonon_contract_primitive,
    )

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

    def _cache_key(self, child, term, term_index: int, cache_mode: str):
        child_idx = self.ttns.node_idx[child]
        if cache_mode == SOP_CACHE_TERM:
            return child_idx, term_index
        if cache_mode == SOP_CACHE_SIGNATURE:
            return child_idx, self.branch_signature(child, term)
        raise ValueError(f"Unsupported SOP cache mode {cache_mode!r}")

    def build_env_cache(self, cache_mode: str = SOP_CACHE_SIGNATURE):
        if cache_mode == SOP_CACHE_NONE:
            return
        for term_index, term in enumerate(self.sop.terms):
            for child in self.active_node.children:
                key = self._cache_key(child, term, term_index, cache_mode)
                if key not in self._env_cache:
                    self._env_cache[key] = self._contract_subtree(child, term, term_index, cache_mode)

    def apply(self, use_env: bool = None, cache_mode: str = None):
        if cache_mode is None:
            cache_mode = SOP_CACHE_SIGNATURE if use_env else SOP_CACHE_NONE
        result = np.zeros_like(self.active_node.tensor)
        for term_index, term in enumerate(self.sop.terms):
            result = result + self._apply_term(term, term_index, cache_mode)
        return result

    def _subtree_postorder(self, node):
        nodes = []
        for child in node.children:
            nodes.extend(self._subtree_postorder(child))
        nodes.append(node)
        return nodes

    def _branch_env(self, child, term, term_index: int, cache_mode: str):
        if cache_mode == SOP_CACHE_NONE:
            return self._contract_subtree(child, term, term_index, SOP_CACHE_NONE)
        key = self._cache_key(child, term, term_index, cache_mode)
        if key not in self._env_cache:
            self._env_cache[key] = self._contract_subtree(child, term, term_index, cache_mode)
        return self._env_cache[key]

    def _parent_env(self, node, term, term_index: int, cache_mode: str):
        if node.parent is None:
            return None
        return self._contract_parent_side(node, term, term_index, cache_mode)

    def _contract_subtree(self, node, term, term_index: int, cache_mode: str):
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
            env = self._branch_env(child, term, term_index, cache_mode)
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

    def _contract_parent_side(self, node, term, term_index: int, cache_mode: str):
        parent = node.parent
        parent_idx = self.ttns.node_idx[parent]
        node_idx = self.ttns.node_idx[node]
        ket = parent.tensor
        factors = self.sop._local_matrix_factors(parent_idx, term.local_ops.get(parent_idx))
        physical_axis0 = len(parent.children)
        for ibasis, mat in enumerate(factors):
            if mat is not None:
                ket = _apply_matrix_on_axis(ket, mat, physical_axis0 + ibasis)

        args = []
        bra_indices = []
        ket_indices = []
        active_bra = active_ket = None
        for child in parent.children:
            child_idx = self.ttns.node_idx[child]
            bra_child = ("sop_parent_bra_child", child_idx)
            ket_child = ("sop_parent_ket_child", child_idx)
            if child is node:
                active_bra = bra_child
                active_ket = ket_child
            else:
                env = self._branch_env(child, term, term_index, cache_mode)
                args.extend([env, [bra_child, ket_child]])
            bra_indices.append(bra_child)
            ket_indices.append(ket_child)

        for iphys in range(len(parent.tensor.shape) - len(parent.children) - 1):
            phys = ("sop_parent_phys", parent_idx, iphys)
            bra_indices.append(phys)
            ket_indices.append(phys)

        if parent.parent is None:
            parent_bond = ("sop_parent_root_bond", parent_idx)
            bra_indices.append(parent_bond)
            ket_indices.append(parent_bond)
        else:
            env = self._parent_env(parent, term, term_index, cache_mode)
            bra_parent = ("sop_parent_bra_parent", parent_idx)
            ket_parent = ("sop_parent_ket_parent", parent_idx)
            args.extend([env, [bra_parent, ket_parent]])
            bra_indices.append(bra_parent)
            ket_indices.append(ket_parent)

        args.extend([parent.tensor.conj(), bra_indices, ket, ket_indices, [active_bra, active_ket]])
        return oe_contract(*args)

    def _apply_term(self, term, term_index: int, cache_mode: str):
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
            env = self._branch_env(child, term, term_index, cache_mode)
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

        if self.active_node.parent is None:
            parent = ("sop_active_parent", self.active_idx)
            tensor_indices.append(parent)
            output_indices.append(parent)
        else:
            env = self._parent_env(self.active_node, term, term_index, cache_mode)
            bra_parent = ("sop_active_bra_parent", self.active_idx)
            ket_parent = ("sop_active_ket_parent", self.active_idx)
            args.extend([env, [bra_parent, ket_parent]])
            tensor_indices.append(ket_parent)
            output_indices.append(bra_parent)
        args.insert(1, tensor_indices)
        args.append(output_indices)
        return oe_contract(*args)


class SOPMCTDHSweepEnvironment:
    """Strict SOP state-environment baseline over a whole one-site sweep.

    The cache key is ``(source_node_idx, target_node_idx, term_index)``.  This
    deliberately preserves the flat SOP term structure: identical operator
    subtrees from different terms are not merged or hashed together.
    """

    def __init__(self, sop: SOPBaselineOperator, ttns: TTNS):
        self.sop = sop
        self.ttns = ttns
        self._env_cache: Dict[Tuple[int, int, int], np.ndarray] = {}

    def build_env_cache(self):
        for term_index, term in enumerate(self.sop.terms):
            for node in self.ttns.postorder_list():
                if node.parent is not None:
                    self._env_cache[self._edge_key(node, node.parent, term_index)] = (
                        self._contract_node_to_parent(node, term, term_index)
                    )
            for parent in self.ttns.node_list:
                for child in parent.children:
                    self._env_cache[self._edge_key(parent, child, term_index)] = (
                        self._contract_parent_to_child(parent, child, term, term_index)
                    )

    def apply(self, active_nodes):
        return [self.apply_node(active_node) for active_node in active_nodes]

    def apply_node(self, active_node):
        active_idx = self.ttns.node_idx[active_node]
        result = np.zeros_like(active_node.tensor)
        for term_index, term in enumerate(self.sop.terms):
            result = result + self._apply_term(active_node, active_idx, term, term_index)
        return result

    def _edge_key(self, source, target, term_index: int):
        return self.ttns.node_idx[source], self.ttns.node_idx[target], term_index

    def _edge_env(self, source, target, term_index: int):
        return self._env_cache[self._edge_key(source, target, term_index)]

    def _contract_node_to_parent(self, node, term, term_index: int):
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
            child_idx = self.ttns.node_idx[child]
            bra_child = ("sop_mctdh_up_bra_child", node_idx, child_idx)
            ket_child = ("sop_mctdh_up_ket_child", node_idx, child_idx)
            args.extend([self._edge_env(child, node, term_index), [bra_child, ket_child]])
            bra_indices.append(bra_child)
            ket_indices.append(ket_child)

        for iphys in range(len(node.tensor.shape) - len(node.children) - 1):
            phys = ("sop_mctdh_up_phys", node_idx, iphys)
            bra_indices.append(phys)
            ket_indices.append(phys)

        bra_parent = ("sop_mctdh_up_bra_parent", node_idx)
        ket_parent = ("sop_mctdh_up_ket_parent", node_idx)
        bra_indices.append(bra_parent)
        ket_indices.append(ket_parent)
        args.extend([node.tensor.conj(), bra_indices, ket, ket_indices, [bra_parent, ket_parent]])
        return oe_contract(*args)

    def _contract_parent_to_child(self, parent, child, term, term_index: int):
        parent_idx = self.ttns.node_idx[parent]
        child_idx = self.ttns.node_idx[child]
        ket = parent.tensor
        factors = self.sop._local_matrix_factors(parent_idx, term.local_ops.get(parent_idx))
        physical_axis0 = len(parent.children)
        for ibasis, mat in enumerate(factors):
            if mat is not None:
                ket = _apply_matrix_on_axis(ket, mat, physical_axis0 + ibasis)

        args = []
        bra_indices = []
        ket_indices = []
        active_bra = active_ket = None
        for sibling in parent.children:
            sibling_idx = self.ttns.node_idx[sibling]
            bra_child = ("sop_mctdh_down_bra_child", parent_idx, sibling_idx)
            ket_child = ("sop_mctdh_down_ket_child", parent_idx, sibling_idx)
            if sibling is child:
                active_bra = bra_child
                active_ket = ket_child
            else:
                args.extend([self._edge_env(sibling, parent, term_index), [bra_child, ket_child]])
            bra_indices.append(bra_child)
            ket_indices.append(ket_child)

        for iphys in range(len(parent.tensor.shape) - len(parent.children) - 1):
            phys = ("sop_mctdh_down_phys", parent_idx, iphys)
            bra_indices.append(phys)
            ket_indices.append(phys)

        if parent.parent is None:
            parent_bond = ("sop_mctdh_down_root_bond", parent_idx)
            bra_indices.append(parent_bond)
            ket_indices.append(parent_bond)
        else:
            bra_parent = ("sop_mctdh_down_bra_parent", parent_idx)
            ket_parent = ("sop_mctdh_down_ket_parent", parent_idx)
            args.extend([self._edge_env(parent.parent, parent, term_index), [bra_parent, ket_parent]])
            bra_indices.append(bra_parent)
            ket_indices.append(ket_parent)

        args.extend([parent.tensor.conj(), bra_indices, ket, ket_indices, [active_bra, active_ket]])
        return oe_contract(*args)

    def _apply_term(self, active_node, active_idx: int, term, term_index: int):
        tensor = active_node.tensor
        factors = self.sop._local_matrix_factors(active_idx, term.local_ops.get(active_idx))
        physical_axis0 = len(active_node.children)
        for ibasis, mat in enumerate(factors):
            if mat is not None:
                tensor = _apply_matrix_on_axis(tensor, mat, physical_axis0 + ibasis)
        tensor = tensor * term.coeff

        args = [tensor]
        tensor_indices = []
        output_indices = []
        for child in active_node.children:
            child_idx = self.ttns.node_idx[child]
            bra_child = ("sop_mctdh_active_bra_child", active_idx, child_idx)
            ket_child = ("sop_mctdh_active_ket_child", active_idx, child_idx)
            args.extend([self._edge_env(child, active_node, term_index), [bra_child, ket_child]])
            tensor_indices.append(ket_child)
            output_indices.append(bra_child)

        for iphys in range(len(tensor.shape) - len(active_node.children) - 1):
            phys = ("sop_mctdh_active_phys", active_idx, iphys)
            tensor_indices.append(phys)
            output_indices.append(phys)

        if active_node.parent is None:
            parent = ("sop_mctdh_active_parent", active_idx)
            tensor_indices.append(parent)
            output_indices.append(parent)
        else:
            bra_parent = ("sop_mctdh_active_bra_parent", active_idx)
            ket_parent = ("sop_mctdh_active_ket_parent", active_idx)
            args.extend([self._edge_env(active_node.parent, active_node, term_index), [bra_parent, ket_parent]])
            tensor_indices.append(ket_parent)
            output_indices.append(bra_parent)
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


def _ttno_active_scope_action(ttns, ttno, active_nodes, timeout_sec: int):
    ttne, env_time, env_mem, env_status = _time_and_memory(lambda: TTNEnviron(ttns, ttno), timeout_sec)
    if env_status != "ok":
        return None, env_time, 0.0, 0.0, env_mem, env_status

    exprs, expr_time, expr_mem, expr_status = _time_and_memory(
        lambda: [hop_expr1(active_node, ttns, ttno, ttne) for active_node in active_nodes],
        timeout_sec,
    )
    if expr_status != "ok":
        return None, env_time, expr_time, 0.0, max(env_mem, expr_mem), expr_status

    actions, apply_time, apply_mem, apply_status = _time_and_memory(
        lambda: [expr(active_node.tensor) for expr, active_node in zip(exprs, active_nodes)],
        timeout_sec,
    )
    return actions, env_time, expr_time, apply_time, max(env_mem, expr_mem, apply_mem), apply_status


def _sop_one_site_action(sop, ttns, active_node, method: str, timeout_sec: int):
    applier = SOPOneSiteEffective(sop, ttns, active_node)
    env_time = 0.0
    env_mem = 0.0
    cache_mode = SOP_METHOD_CACHE_MODE[method]
    if cache_mode != SOP_CACHE_NONE:
        _, env_time, env_mem, env_status = _time_and_memory(lambda: applier.build_env_cache(cache_mode), timeout_sec)
        if env_status != "ok":
            return None, env_time, 0.0, 0.0, env_mem, env_status, len(applier._env_cache)
    action, apply_time, apply_mem, apply_status = _time_and_memory(
        lambda: applier.apply(cache_mode=cache_mode), timeout_sec
    )
    return action, env_time, 0.0, apply_time, max(env_mem, apply_mem), apply_status, len(applier._env_cache)


def _sop_active_scope_action(sop, ttns, active_nodes, method: str, timeout_sec: int):
    if method == "sop_mctdh_like_state_env" and len(active_nodes) > 1:
        applier = SOPMCTDHSweepEnvironment(sop, ttns)
        _, env_time, env_mem, env_status = _time_and_memory(applier.build_env_cache, timeout_sec)
        if env_status != "ok":
            return None, env_time, 0.0, 0.0, env_mem, env_status, len(applier._env_cache)
        actions, apply_time, apply_mem, apply_status = _time_and_memory(
            lambda: applier.apply(active_nodes), timeout_sec
        )
        return (
            actions,
            env_time,
            0.0,
            apply_time,
            max(env_mem, apply_mem),
            apply_status,
            len(applier._env_cache),
        )

    actions = []
    env_time = 0.0
    expr_time = 0.0
    apply_time = 0.0
    memory_mb = 0.0
    n_env_cache_entries = 0
    for active_node in active_nodes:
        action, node_env_t, node_expr_t, node_apply_t, node_mem, status, node_cache_entries = _sop_one_site_action(
            sop, ttns, active_node, method, timeout_sec
        )
        env_time += node_env_t
        expr_time += node_expr_t
        apply_time += node_apply_t
        memory_mb = max(memory_mb, node_mem)
        n_env_cache_entries += node_cache_entries
        if status != "ok":
            return None, env_time, expr_time, apply_time, memory_mb, status, n_env_cache_entries
        actions.append(action)
    return actions, env_time, expr_time, apply_time, memory_mb, "ok", n_env_cache_entries


def _relative_error(action, reference):
    if action is None or reference is None:
        return math.nan
    if isinstance(action, list) or isinstance(reference, list):
        if not isinstance(action, list) or not isinstance(reference, list) or len(action) != len(reference):
            return math.nan
        denom_sq = 0.0
        diff_sq = 0.0
        for item, ref_item in zip(action, reference):
            item = np.asarray(item)
            ref_item = np.asarray(ref_item)
            denom_sq += float(np.linalg.norm(ref_item.ravel()) ** 2)
            diff_sq += float(np.linalg.norm((item - ref_item).ravel()) ** 2)
        return math.sqrt(diff_sq / denom_sq) if denom_sq != 0 else math.sqrt(diff_sq)
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


def _tree_depth(node):
    if not node.children:
        return 1
    return 1 + max(_tree_depth(child) for child in node.children)


def _active_nodes(psi, active_scope: str):
    if active_scope == "root":
        return [psi.root]
    if active_scope == "all_nodes":
        return list(psi.node_list)
    raise ValueError(f"Unsupported active scope {active_scope!r}")


def _point_metadata(path_name, n_lead, n_phonon, tree, psi, sop, ttno, active_nodes, active_scope, git_commit):
    n_fermion_sites = 4 * n_lead + 2
    n_boson_sites = n_phonon
    n_total_sites = n_fermion_sites + n_boson_sites
    n_active_nodes = len(active_nodes)
    tree_depth = _tree_depth(psi.root)
    active_node_idx = tree.node_idx[tree.root] if active_scope == "root" else "all"
    quantity = "local_effective_1site_apply" if active_scope == "root" else "local_effective_1site_apply_all_nodes"
    return {
        "case_name": "hubbard_junction",
        "scaling_path": path_name,
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_fermion_sites": n_fermion_sites,
        "n_boson_sites": n_boson_sites,
        "n_total_sites": n_total_sites,
        "n_sop_terms": sop.n_terms,
        "n_active_nodes": n_active_nodes,
        "tree_depth": tree_depth,
        "n_sop_terms_times_n_total_sites": sop.n_terms * n_total_sites,
        "n_sop_terms_times_n_active_nodes": sop.n_terms * n_active_nodes,
        "n_sop_terms_times_tree_depth": sop.n_terms * tree_depth,
        "ttno_max_bond": max(ttno.bond_dims),
        "ttno_mean_bond": float(onp.mean(ttno.bond_dims)),
        "state_max_bond": max(psi.bond_dims),
        "local_basis_summary": _local_dim_summary(tree),
        "active_node_idx": active_node_idx,
        "quantity": quantity,
        "backend": "cpu",
        "num_threads": os.environ.get("RENO_NUM_THREADS", ""),
        "git_commit": git_commit,
    }


def _method_row(metadata, method, repeat_id, env_t, expr_t, term_loop_t, apply_t, mem_mb, rel_err, status,
                n_env_cache_entries=0):
    return {
        **metadata,
        "method": method,
        "repeat_id": repeat_id,
        "time_env_build_sec": env_t,
        "time_expr_build_sec": expr_t,
        "time_term_loop_sec": term_loop_t,
        "time_apply_sec": apply_t,
        "time_total_sec": env_t + expr_t + apply_t,
        "n_env_cache_entries": n_env_cache_entries,
        "memory_peak_mb": mem_mb,
        "relative_error_vs_ttno": rel_err,
        "status": status,
        "overhead_region": "",
    }


def _run_point(
    path_name,
    n_lead,
    n_phonon,
    repeat_id,
    args,
    git_commit,
    skip_methods=frozenset(),
    state_bond_dim: int = 1,
    primitive_basis_dim: int = None,
    selected_methods=METHODS,
):
    tree, terms, psi = build_hubbard_junction_case(
        n_lead,
        n_phonon,
        max_phonon_basis=args.max_phonon_basis,
        force_phonon_basis=primitive_basis_dim,
    )
    if state_bond_dim > 1:
        psi = TTNS.random(tree, qntot=0, m_max=state_bond_dim)
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    active_nodes = _active_nodes(psi, args.active_scope)
    metadata = _point_metadata(path_name, n_lead, n_phonon, tree, psi, sop, ttno, active_nodes, args.active_scope, git_commit)

    rows = []
    selected_methods = tuple(selected_methods)
    needs_ttno_reference = "ttno_with_env" in selected_methods or any(
        method.startswith("sop_") for method in selected_methods
    )
    if not needs_ttno_reference:
        ref = None
    elif "ttno_with_env" in skip_methods:
        ref = None
        if "ttno_with_env" in selected_methods:
            rows.append(_method_row(
                metadata, "ttno_with_env", repeat_id, 0.0, 0.0, 0.0, 0.0, 0.0, math.nan,
                "skipped_after_previous_timeout_or_memory",
            ))
    else:
        ref, env_t, expr_t, apply_t, mem_mb, status = _ttno_active_scope_action(psi, ttno, active_nodes, args.timeout_sec)
        if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
            status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"
        if "ttno_with_env" in selected_methods:
            rows.append(_method_row(
                metadata, "ttno_with_env", repeat_id, env_t, expr_t, 0.0, apply_t, mem_mb,
                0.0 if status == "ok" else math.nan, status,
            ))

    for method in ("sop_no_env", "sop_mctdh_like_state_env", "sop_env_plus_operator_cache"):
        if method not in selected_methods:
            continue
        if method in skip_methods:
            rows.append(_method_row(
                metadata, method, repeat_id, 0.0, 0.0, 0.0, 0.0, 0.0, math.nan,
                "skipped_after_previous_timeout_or_memory",
            ))
            continue
        action, env_t, expr_t, apply_t, mem_mb, status, n_env_cache_entries = _sop_active_scope_action(
            sop, psi, active_nodes, method, args.timeout_sec
        )
        if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
            status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"
        rows.append(_method_row(
            metadata, method, repeat_id, env_t, expr_t, apply_t, apply_t, mem_mb,
            _relative_error(action, ref) if status == "ok" else math.nan, status,
            n_env_cache_entries=n_env_cache_entries,
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


def _make_point(n_lead: int, n_phonon: int, state_bond_dim: int = 1, primitive_basis_dim: int = None):
    return (n_lead, n_phonon, state_bond_dim, primitive_basis_dim)


def _unpack_point(point):
    if len(point) == 2:
        n_lead, n_phonon = point
        return n_lead, n_phonon, 1, None
    return point


def _scaling_points(args):
    paths = []
    if args.scaling_path in ("lead_only", "all", "ren_variables"):
        leads = _parse_int_list(args.lead_values)
        paths.append(("lead_only", [_make_point(n, 0) for n in leads]))
    if args.scaling_path in ("balanced_lead_phonon", "all"):
        paths.append(("balanced_lead_phonon", _parse_pairs(args.balanced_pairs)))
    if args.scaling_path in ("state_bond", "ren_variables", "ren_aux"):
        paths.append((
            "state_bond",
            [
                _make_point(args.state_bond_base_lead, args.state_bond_base_phonon, m, None)
                for m in _parse_int_list(args.state_bond_values)
            ],
        ))
    if args.scaling_path in ("primitive_basis", "ren_variables", "ren_aux"):
        state_bond_dim = getattr(args, "primitive_basis_state_bond", 1)
        paths.append((
            "primitive_basis",
            [
                _make_point(args.primitive_basis_base_lead, args.primitive_basis_base_phonon, state_bond_dim, d)
                for d in _parse_int_list(args.primitive_basis_values)
            ],
        ))
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
    distinct_x = {float(r[x_axis]) for r in used}
    if len(used) < 2 or len(distinct_x) < 2:
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
    x_axes = [
        "n_total_sites",
        "n_sop_terms",
        "n_lead",
        "n_phonon",
        "n_sop_terms_times_n_total_sites",
        "n_sop_terms_times_n_active_nodes",
        "n_sop_terms_times_tree_depth",
    ]
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


def write_csv_atomic(path, rows, fields):
    temporary = path.with_suffix(path.suffix + ".tmp")
    write_csv(temporary, rows, fields)
    temporary.replace(path)


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
            n_lead, n_phonon, state_bond_dim, primitive_basis_dim = _unpack_point(points[idx])
            point_rows = []
            for repeat_id in range(args.repeats):
                try:
                    repeat_rows = _run_point(
                        path_name,
                        n_lead,
                        n_phonon,
                        repeat_id,
                        args,
                        git_commit,
                        disabled_methods,
                        state_bond_dim=state_bond_dim,
                        primitive_basis_dim=primitive_basis_dim,
                    )
                except Exception as exc:
                    repeat_rows = [{
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
                    }]
                point_rows.extend(repeat_rows)
                rows.extend(repeat_rows)
                write_csv_atomic(args.output, rows, RAW_FIELDS)
            for row in point_rows:
                if row.get("method") in METHODS and _is_resource_failure(row.get("status")):
                    disabled_methods.add(row["method"])
            ok_methods = {r["method"] for r in point_rows if str(r["status"]).startswith("ok")}
            if not ok_methods:
                consecutive_hard_failures += 1
            else:
                consecutive_hard_failures = 0
            mark_overhead_rows(rows)
            fits = compute_fits(rows, args.alpha_stability_tol)
            write_csv_atomic(args.output, rows, RAW_FIELDS)
            write_csv_atomic(args.fit_output, fits, FIT_FIELDS)
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
                    last_lead, last_phonon, last_state_bond, last_primitive_basis = _unpack_point(points[-1])
                    if path_name == "lead_only":
                        points.append(_make_point(last_lead * 2, 0))
                    elif path_name == "balanced_lead_phonon":
                        points.append((last_lead * 2, max(last_phonon * 2, 1)))
                    elif path_name == "state_bond":
                        points.append(_make_point(last_lead, last_phonon, last_state_bond * 2, None))
                    elif path_name == "primitive_basis":
                        points.append(_make_point(
                            last_lead,
                            last_phonon,
                            last_state_bond,
                            last_primitive_basis * 2,
                        ))
                    extra_used += 1

    mark_overhead_rows(rows)
    fits = compute_fits(rows, args.alpha_stability_tol)
    write_csv_atomic(args.output, rows, RAW_FIELDS)
    write_csv_atomic(args.fit_output, fits, FIT_FIELDS)
    save_plots(rows, args.output.with_suffix(""))
    return rows, fits


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scaling-path",
        choices=["lead_only", "balanced_lead_phonon", "state_bond", "primitive_basis", "ren_aux", "ren_variables", "all"],
        default="all",
    )
    parser.add_argument("--lead-values", default="4 8 16 32 64 128")
    parser.add_argument("--balanced-pairs", default="4:1 8:2 16:4 32:8 64:16")
    parser.add_argument("--state-bond-values", default="1 2 4 8 16")
    parser.add_argument("--primitive-basis-values", default="2 4 8 16")
    parser.add_argument("--state-bond-base-lead", type=int, default=8)
    parser.add_argument("--state-bond-base-phonon", type=int, default=0)
    parser.add_argument("--primitive-basis-base-lead", type=int, default=4)
    parser.add_argument("--primitive-basis-base-phonon", type=int, default=4)
    parser.add_argument("--primitive-basis-state-bond", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-sec", type=int, default=1800)
    parser.add_argument("--memory-limit-mb", type=float, default=0.0)
    parser.add_argument("--max-extra-points", type=int, default=1)
    parser.add_argument("--stop-after-consecutive-failures", type=int, default=2)
    parser.add_argument("--alpha-stability-tol", type=float, default=0.25)
    parser.add_argument("--max-phonon-basis", type=int, default=4)
    parser.add_argument("--active-scope", choices=["root", "all_nodes"], default="root")
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
