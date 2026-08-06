#!/usr/bin/env python3
"""Run one Hubbard-junction balanced lead/phonon supplementary task."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as onp

from benchmarks.benchmark_adaptive_operator_env import (
    _active_nodes,
    _local_dim_summary,
    _method_row,
    _relative_error,
    _sop_active_scope_action,
    _tree_depth,
    _ttno_active_scope_action,
    build_hubbard_junction_case,
)
from benchmarks.hubbard_balanced_manifest import read_task
from renormalizer.mps.backend import np
from renormalizer.tn import SOPBaselineOperator, TTNO, TTNS


RNG_SEED = 202407


def _point_seed(n_lead, n_phonon, state_bond, primitive_basis):
    return (
        RNG_SEED + 100003 * n_lead + 1009 * n_phonon + 17 * state_bond + primitive_basis
    ) % (2**32)


def _json_default(value):
    if isinstance(value, onp.generic):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


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


def snapshot_path(snapshot_dir, task):
    return (
        snapshot_dir
        / f"task_{task.task_id:04d}_repeat_{task.repeat_id}.npz"
    )


def run_hubbard_balanced_point(
    n_lead,
    n_phonon,
    state_bond,
    primitive_basis,
    method,
    repeat_id,
    args,
    git_commit,
):
    tree, terms, psi = build_hubbard_junction_case(
        n_lead=n_lead,
        n_phonon=n_phonon,
        max_phonon_basis=primitive_basis,
        force_phonon_basis=primitive_basis,
        phonon_contract_primitive=False,
    )
    seed = _point_seed(n_lead, n_phonon, state_bond, primitive_basis)
    onp.random.seed(seed)
    np.random.seed(seed)
    if state_bond > 1:
        psi = TTNS.random(tree, qntot=0, m_max=state_bond)

    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    active_nodes = _active_nodes(psi, args.active_scope)
    metadata = {
        "case_name": "hubbard_junction",
        "panel": "balanced",
        "n_lead": n_lead,
        "n_phonon": n_phonon,
        "n_fermion_sites": 4 * n_lead + 2,
        "n_boson_sites": n_phonon,
        "n_total_sites": 4 * n_lead + 2 + n_phonon,
        "n_sop_terms": sop.n_terms,
        "n_active_nodes": len(active_nodes),
        "tree_depth": _tree_depth(psi.root),
        "target_state_bond": state_bond,
        "state_max_bond": max(psi.bond_dims),
        "primitive_basis_dim": primitive_basis,
        "contract_primitive": False,
        "phonon_tree_layout": "paired_no_contraction",
        "ttno_max_bond": max(ttno.bond_dims),
        "ttno_mean_bond": float(onp.mean(ttno.bond_dims)),
        "state_tensor_elements": int(sum(node.tensor.size for node in psi.node_list)),
        "operator_tensor_elements": int(sum(node.tensor.size for node in ttno.node_list)),
        "local_basis_summary": _local_dim_summary(tree),
        "active_node_idx": "all",
        "quantity": "local_effective_1site_apply_all_nodes",
        "backend": "cpu",
        "num_threads": "1",
        "git_commit": git_commit,
    }

    ref, env_t, expr_t, apply_t, mem_mb, status = _ttno_active_scope_action(
        psi, ttno, active_nodes, args.timeout_sec
    )
    if status == "ok" and args.memory_limit_mb > 0 and mem_mb > args.memory_limit_mb:
        status = f"memory_limit_exceeded: {mem_mb:.1f} MB > {args.memory_limit_mb:.1f} MB"

    rows = []
    if method == "ttno_with_env":
        rows.append(_method_row(
            metadata,
            "ttno_with_env",
            repeat_id,
            env_t,
            expr_t,
            0.0,
            apply_t,
            mem_mb,
            0.0 if status == "ok" else onp.nan,
            status,
        ))
    else:
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
            else onp.nan,
            method_status,
            n_env_cache_entries=cache_entries,
        ))
    return rows


def run_task(task, snapshot_dir, timeout_sec, memory_limit_mb, git_commit):
    output = snapshot_path(snapshot_dir, task)
    args = SimpleNamespace(
        timeout_sec=timeout_sec,
        memory_limit_mb=memory_limit_mb,
        active_scope="all_nodes",
    )
    try:
        rows = run_hubbard_balanced_point(
            n_lead=task.n_lead,
            n_phonon=task.n_phonon,
            state_bond=task.state_bond,
            primitive_basis=task.primitive_basis,
            method=task.method,
            repeat_id=task.repeat_id,
            args=args,
            git_commit=git_commit,
        )
        if len(rows) != 1:
            raise RuntimeError(f"expected one method row, got {len(rows)}")
        payload = {**asdict(task), **rows[0], "snapshot_version": 1}
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            **asdict(task),
            "snapshot_version": 1,
            "status": f"error: {type(exc).__name__}: {exc}",
        }
        write_snapshot_atomic(output, payload)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=39600)
    parser.add_argument("--memory-limit-mb", type=float, default=60000)
    parser.add_argument("--git-commit", default="hubbard-balanced")
    args = parser.parse_args()
    task = read_task(args.manifest, args.task_id)
    output, payload = run_task(
        task,
        args.snapshot_dir,
        args.timeout_sec,
        args.memory_limit_mb,
        args.git_commit,
    )
    print(f"Wrote {output}")
    print(json.dumps(payload, sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
