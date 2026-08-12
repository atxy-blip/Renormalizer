#!/usr/bin/env python3
"""Run one Hubbard-junction per-node profiling task.

Measures, for every TTNS node, the one-site local-action wall time of
sop_no_env, sop_mctdh_like_state_env, and ttno_with_env on the same
molecular-junction state. The strict and TTNO environments are built once
per point; per-node timing covers only the local action itself.
"""

import argparse
import json
import time
from pathlib import Path

import numpy as onp

from benchmarks.benchmark_adaptive_operator_env import (
    SOP_CACHE_NONE,
    SOPMCTDHSweepEnvironment,
    SOPOneSiteEffective,
    build_hubbard_junction_case,
)
from benchmarks.hubbard_pernode_manifest import (
    HUBBARD_PRIMITIVE_BASIS,
    HUBBARD_STATE_BOND,
    point_for_task,
)
from renormalizer.mps.backend import np
from renormalizer.tn import SOPBaselineOperator, TTNO, TTNS
from renormalizer.tn.hop_expr import hop_expr1
from renormalizer.tn.tree import TTNEnviron


RNG_SEED = 202407


def _json_default(value):
    if isinstance(value, onp.generic):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def classify_tree_node(tree_node):
    """Return a coarse physical role for a BasisTree node."""

    basis = list(tree_node.basis_sets)
    if any(b.__class__.__name__ == "BasisSHO" for b in basis):
        return "phonon"
    half_spins = [b for b in basis if b.__class__.__name__ == "BasisHalfSpin"]
    if half_spins:
        dof = half_spins[0].dofs[0]
        if dof.startswith(("L", "R")):
            return "lead"
        if dof.startswith("s"):
            return "bridge"
        return "other"
    return "internal"


def compute_support_loads(sop, psi):
    """Number of SOP terms whose support contains each TTNS node."""

    loads = {idx: 0 for idx in range(len(psi.node_list))}
    for term in sop.terms:
        for idx in term.local_ops:
            loads[idx] += 1
    return loads


def node_depths(psi):
    depths = {}
    stack = [(psi.root, 0)]
    while stack:
        node, depth = stack.pop()
        depths[psi.node_idx[node]] = depth
        stack.extend((child, depth + 1) for child in node.children)
    return depths


def write_snapshot_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as f:
        onp.savez_compressed(
            f,
            payload_json=onp.asarray(json.dumps(payload, sort_keys=True, default=_json_default)),
        )
    temporary.replace(path)


def load_snapshot(path):
    with onp.load(path, allow_pickle=False) as data:
        return json.loads(str(data["payload_json"]))


def snapshot_path(snapshot_dir, task_id):
    return snapshot_dir / f"task_{task_id:04d}.npz"


def run_pernode_point(n_lead, n_phonon, timeout_sec, memory_limit_mb):
    tree, terms, psi = build_hubbard_junction_case(
        n_lead=n_lead,
        n_phonon=n_phonon,
        max_phonon_basis=HUBBARD_PRIMITIVE_BASIS,
        force_phonon_basis=HUBBARD_PRIMITIVE_BASIS,
        phonon_contract_primitive=False,
    )
    seed = (RNG_SEED + 100003 * n_lead + 1009 * n_phonon) % (2**32)
    onp.random.seed(seed)
    np.random.seed(seed)
    if HUBBARD_STATE_BOND > 1:
        psi = TTNS.random(tree, qntot=0, m_max=HUBBARD_STATE_BOND)

    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    tree_nodes = list(tree.node_list)
    psi_nodes = list(psi.node_list)
    if len(tree_nodes) != len(psi_nodes):
        raise RuntimeError("tree/psi node list length mismatch")
    for tree_node, psi_node in zip(tree_nodes, psi_nodes):
        if len(tree_node.children) != len(psi_node.children):
            raise RuntimeError("tree/psi node order mismatch")

    node_roles = [classify_tree_node(tn) for tn in tree_nodes]
    support_loads = compute_support_loads(sop, psi)
    depths = node_depths(psi)

    t0 = time.perf_counter()
    times_no_env = []
    for psi_node in psi_nodes:
        applier = SOPOneSiteEffective(sop, psi, psi_node)
        start = time.perf_counter()
        applier.apply(cache_mode=SOP_CACHE_NONE)
        times_no_env.append(time.perf_counter() - start)
    no_env_total = time.perf_counter() - t0

    t0 = time.perf_counter()
    strict_env = SOPMCTDHSweepEnvironment(sop, psi)
    strict_env.build_env_cache()
    strict_env_build = time.perf_counter() - t0
    times_strict = []
    for psi_node in psi_nodes:
        start = time.perf_counter()
        strict_env.apply_node(psi_node)
        times_strict.append(time.perf_counter() - start)
    strict_total = strict_env_build + sum(times_strict)

    t0 = time.perf_counter()
    ttne = TTNEnviron(psi, ttno)
    ttno_env_build = time.perf_counter() - t0
    times_ttno = []
    for psi_node in psi_nodes:
        expr = hop_expr1(psi_node, psi, ttno, ttne)
        start = time.perf_counter()
        expr(psi_node.tensor)
        times_ttno.append(time.perf_counter() - start)
    ttno_total = ttno_env_build + sum(times_ttno)

    rows = []
    for idx, (psi_node, role) in enumerate(zip(psi_nodes, node_roles)):
        rows.append({
            "node_idx": idx,
            "node_role": role,
            "depth": depths[idx],
            "support_load": support_loads[idx],
            "time_no_env_sec": times_no_env[idx],
            "time_strict_env_sec": times_strict[idx],
            "time_ttno_sec": times_ttno[idx],
        })

    peak_mb = max(
        onp.asarray(t).nbytes for t in psi_nodes
    ) / 1024 / 1024
    return {
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_total_sites": 4 * n_lead + 2 + n_phonon,
        "n_nodes": len(rows),
        "state_max_bond": max(psi.bond_dims),
        "ttno_max_bond": max(ttno.bond_dims),
        "no_env_total_sec": no_env_total,
        "strict_env_build_sec": strict_env_build,
        "strict_total_sec": strict_total,
        "ttno_env_build_sec": ttno_env_build,
        "ttno_total_sec": ttno_total,
        "state_tensor_bytes_mb": peak_mb,
        "rows": rows,
        "status": "ok",
    }


def run_task(task_id, snapshot_dir, timeout_sec, memory_limit_mb):
    n_lead, n_phonon = point_for_task(task_id)
    output = snapshot_path(snapshot_dir, task_id)
    try:
        payload = run_pernode_point(n_lead, n_phonon, timeout_sec, memory_limit_mb)
        payload["task_id"] = task_id
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            "task_id": task_id,
            "n_lead": n_lead,
            "n_phonon": n_phonon,
            "status": f"error: {type(exc).__name__}: {exc}",
        }
        write_snapshot_atomic(output, payload)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=3600)
    parser.add_argument("--memory-limit-mb", type=float, default=30000)
    args = parser.parse_args()
    output, payload = run_task(
        args.task_id, args.snapshot_dir, args.timeout_sec, args.memory_limit_mb
    )
    print(f"Wrote {output}")
    print(json.dumps(payload, sort_keys=True, default=_json_default)[:2000])


if __name__ == "__main__":
    main()
