#!/usr/bin/env python3
"""Li.W.2024 spin--boson setup for the three operator-environment kernels."""

import math

import numpy as onp

from benchmarks.benchmark_adaptive_operator_env import (
    _active_nodes,
    _local_dim_summary,
    _method_row,
    _relative_error,
    _sop_active_scope_action,
    _tree_depth,
    _ttno_active_scope_action,
)
from benchmarks.li2024_formal_manifest import FORMAL_METHODS, uses_primitive_contraction
from renormalizer import BasisHalfSpin, BasisSHO, Op
from renormalizer.mps.backend import np
from renormalizer.sbm import SpectralDensityFunction
from renormalizer.tn import BasisTree, SOPBaselineOperator, TTNO, TTNS, TreeNodeBasis


RNG_SEED = 202407


def _point_seed(n_modes, state_bond, primitive_basis):
    return (RNG_SEED + 100003 * n_modes + 1009 * state_bond + primitive_basis) % (2**32)


def build_li2024_spin_boson_case(
    n_modes: int,
    state_bond: int,
    primitive_basis: int,
    contract_primitive: bool,
):
    """Build the sub-Ohmic binary TTNS case used for the Li.W.2024 scaling scan."""

    n_modes = int(n_modes)
    state_bond = int(state_bond)
    primitive_basis = int(primitive_basis)
    if n_modes < 2 or min(state_bond, primitive_basis) < 1:
        raise ValueError("n_modes >= 2 and positive dimensions are required")
    expected = uses_primitive_contraction(state_bond, primitive_basis)
    if bool(contract_primitive) != expected:
        raise ValueError(
            "Li.W.2024 adaptive topology requires contract_primitive == (d > M_s); "
            f"got M_s={state_bond}, d={primitive_basis}, contract_primitive={contract_primitive}"
        )

    # Section III A: s=0.5, omega_c=20 Delta, alpha=0.05, Delta=1.
    sdf = SpectralDensityFunction(alpha=0.05, omega_c=20.0, s=0.5)
    frequencies, coupling_squared = sdf.Wang1(n_modes)
    couplings = np.sqrt(coupling_squared)

    spin_basis = BasisHalfSpin("spin", [0, 0])
    phonon_basis = [
        BasisSHO(f"v_{mode}", frequencies[mode], primitive_basis)
        for mode in range(n_modes)
    ]
    terms = [Op("sigma_x", "spin", factor=1.0, qn=0)]
    for mode in range(n_modes):
        dof = f"v_{mode}"
        terms.extend([
            Op("p^2", dof, factor=0.5, qn=0),
            Op("x^2", dof, factor=0.5 * frequencies[mode] ** 2, qn=0),
            Op("sigma_z x", ["spin", dof], factor=couplings[mode], qn=[0, 0]),
        ])

    contract_label = [bool(contract_primitive)] * n_modes
    root = BasisTree.binary_mctdh(
        phonon_basis,
        contract_primitive=True,
        contract_label=contract_label,
        dummy_label="li2024-phonon",
    ).root
    root.add_child(TreeNodeBasis([spin_basis]))
    tree = BasisTree(root)

    seed = _point_seed(n_modes, state_bond, primitive_basis)
    onp.random.seed(seed)
    np.random.seed(seed)
    psi = TTNS.random(tree, qntot=0, m_max=state_bond)
    return tree, terms, psi


def _phonon_leaf_profile(tree):
    counts = []
    for node in tree.node_list:
        count = sum(basis.__class__.__name__ == "BasisSHO" for basis in node.basis_sets)
        if count:
            counts.append(count)
    return counts


def _metadata(
    panel,
    n_modes,
    state_bond,
    primitive_basis,
    contract_primitive,
    tree,
    psi,
    sop,
    ttno,
    active_nodes,
    active_scope,
    git_commit,
):
    n_active_nodes = len(active_nodes)
    tree_depth = _tree_depth(psi.root)
    quantity = (
        "local_effective_1site_apply"
        if active_scope == "root"
        else "local_effective_1site_apply_all_nodes"
    )
    leaf_profile = _phonon_leaf_profile(tree)
    return {
        "case_name": "li2024_spin_boson",
        "panel": panel,
        "scaling_path": panel,
        "n_lead": 0,
        "n_modes": n_modes,
        "n_phonon": n_modes,
        "n_fermion_sites": 1,
        "n_boson_sites": n_modes,
        "n_total_sites": n_modes + 1,
        "n_sop_terms": sop.n_terms,
        "n_active_nodes": n_active_nodes,
        "tree_depth": tree_depth,
        "n_sop_terms_times_n_total_sites": sop.n_terms * (n_modes + 1),
        "n_sop_terms_times_n_active_nodes": sop.n_terms * n_active_nodes,
        "n_sop_terms_times_tree_depth": sop.n_terms * tree_depth,
        "target_state_bond": state_bond,
        "state_max_bond": max(psi.bond_dims),
        "primitive_basis_dim": primitive_basis,
        "contract_primitive": bool(contract_primitive),
        "phonon_tree_layout": (
            "primitive_contracted" if contract_primitive else "paired_no_contraction"
        ),
        "n_phonon_leaf_nodes": len(leaf_profile),
        "max_primitive_modes_per_leaf": max(leaf_profile),
        "ttno_max_bond": max(ttno.bond_dims),
        "ttno_mean_bond": float(onp.mean(ttno.bond_dims)),
        "state_tensor_elements": int(sum(node.tensor.size for node in psi.node_list)),
        "operator_tensor_elements": int(sum(node.tensor.size for node in ttno.node_list)),
        "local_basis_summary": _local_dim_summary(tree),
        "active_node_idx": tree.node_idx[tree.root] if active_scope == "root" else "all",
        "quantity": quantity,
        "backend": "cpu",
        "num_threads": "1",
        "git_commit": git_commit,
    }


def run_li2024_point(
    panel,
    n_modes,
    state_bond,
    primitive_basis,
    contract_primitive,
    repeat_id,
    args,
    git_commit,
    selected_methods=FORMAL_METHODS,
):
    """Run selected operator methods on one Li.W.2024 binary-tree point."""

    selected_methods = tuple(selected_methods)
    unsupported = set(selected_methods) - set(FORMAL_METHODS)
    if unsupported:
        raise ValueError(f"unsupported Li.W.2024 methods: {sorted(unsupported)}")

    tree, terms, psi = build_li2024_spin_boson_case(
        n_modes=n_modes,
        state_bond=state_bond,
        primitive_basis=primitive_basis,
        contract_primitive=contract_primitive,
    )
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    active_nodes = _active_nodes(psi, args.active_scope)
    metadata = _metadata(
        panel,
        n_modes,
        state_bond,
        primitive_basis,
        contract_primitive,
        tree,
        psi,
        sop,
        ttno,
        active_nodes,
        args.active_scope,
        git_commit,
    )

    ref, env_t, expr_t, apply_t, mem_mb, status = _ttno_active_scope_action(
        psi, ttno, active_nodes, args.timeout_sec
    )
    if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
        status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"

    rows = []
    if "ttno_with_env" in selected_methods:
        rows.append(_method_row(
            metadata,
            "ttno_with_env",
            repeat_id,
            env_t,
            expr_t,
            0.0,
            apply_t,
            mem_mb,
            0.0 if status == "ok" else math.nan,
            status,
        ))

    for method in ("sop_no_env", "sop_mctdh_like_state_env"):
        if method not in selected_methods:
            continue
        action, method_env_t, method_expr_t, method_apply_t, method_mem, method_status, cache_entries = (
            _sop_active_scope_action(sop, psi, active_nodes, method, args.timeout_sec)
        )
        if (
            method_status == "ok"
            and args.memory_limit_mb > 0
            and method_mem > args.memory_limit_mb
        ):
            method_status = (
                f"memory_limit_exceeded: {method_mem:.1f} MB > {args.memory_limit_mb:.1f} MB"
            )
        rows.append(_method_row(
            metadata,
            method,
            repeat_id,
            method_env_t,
            method_expr_t,
            0.0,
            method_apply_t,
            method_mem,
            _relative_error(action, ref)
            if method_status == "ok" and status == "ok"
            else math.nan,
            method_status,
            n_env_cache_entries=cache_entries,
        ))
    return rows
