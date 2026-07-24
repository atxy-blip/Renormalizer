#!/usr/bin/env python3
"""Run one recoverable contraction-scaling diagnostic task."""

import argparse
import json
import resource
import time
from dataclasses import asdict
from pathlib import Path

from benchmarks.benchmark_adaptive_operator_env import build_hubbard_junction_case
import opt_einsum as oe
from benchmarks.contraction_scaling_diagnostics import (
    kernel_path_metrics,
    kernel_spec,
    read_task,
)
from renormalizer.mps.backend import np
from renormalizer.tn import TTNO, TTNS
from renormalizer.tn.hop_expr import hop_expr1
from renormalizer.tn.tree import TTNEnviron


def _json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def write_snapshot_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as f:
        np.savez_compressed(
            f,
            payload_json=np.asarray(json.dumps(payload, sort_keys=True, default=_json_default)),
        )
    temporary.replace(path)


def load_snapshot(path):
    with np.load(path, allow_pickle=False) as data:
        return json.loads(str(data["payload_json"]))


def snapshot_path(snapshot_dir, task):
    return (
        snapshot_dir
        / task.panel
        / task.kernel
        / f"task_{task.task_id:04d}_repeat_{task.repeat_id}.npz"
    )


def _peak_memory_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def _timed(fn):
    start = time.perf_counter()
    value = fn()
    return value, time.perf_counter() - start


def _run_dense_kernel(task):
    spec = kernel_spec(
        task.kernel,
        task.state_bond,
        task.primitive_basis,
        task.operator_bond,
    )
    metrics = kernel_path_metrics(
        task.kernel,
        task.state_bond,
        task.primitive_basis,
        task.operator_bond,
    )

    operands, allocation_sec = _timed(
        lambda: [np.ones(shape, dtype=np.float64) for shape in spec["shapes"]]
    )
    constants = list(range(spec["constant_count"]))
    expression, expression_sec = _timed(
        lambda: oe.contract_expression(
            spec["equation"],
            *operands[:-1],
            operands[-1].shape,
            constants=constants,
            optimize="optimal",
        )
    )

    expression(operands[-1])
    output, apply_sec = _timed(lambda: expression(operands[-1]))
    return {
        **metrics,
        "allocation_sec": allocation_sec,
        "expression_build_sec": expression_sec,
        "apply_sec": apply_sec,
        "output_shape": list(output.shape),
        "checksum": float(np.linalg.norm(output.ravel()[: min(output.size, 1024)])),
        "peak_memory_mb": _peak_memory_mb(),
        "status": "ok",
    }


def _phonon_leaf_shapes(tree, tensors):
    shapes = []
    for basis_node, tensor_node in zip(tree.node_list, tensors.node_list):
        sho_count = sum(
            basis.__class__.__name__ == "BasisSHO"
            for basis in basis_node.basis_sets
        )
        if sho_count:
            shapes.append({
                "sho_count": sho_count,
                "shape": list(tensor_node.shape),
            })
    return shapes


def _run_model_kernel(task):
    build_args = dict(
        n_lead=1,
        n_phonon=16,
        force_phonon_basis=task.primitive_basis,
        max_phonon_basis=task.primitive_basis,
        phonon_contract_primitive=task.contract_primitive,
    )
    (tree, terms, _), model_build_sec = _timed(
        lambda: build_hubbard_junction_case(**build_args)
    )
    psi, state_build_sec = _timed(
        lambda: TTNS.random(tree, qntot=0, m_max=task.state_bond)
    )
    ttno, operator_build_sec = _timed(lambda: TTNO(tree, terms))
    environ, environment_build_sec = _timed(lambda: TTNEnviron(psi, ttno))
    expressions, expression_build_sec = _timed(
        lambda: [hop_expr1(node, psi, ttno, environ) for node in psi.node_list]
    )
    actions, apply_sec = _timed(
        lambda: [expr(node.tensor) for expr, node in zip(expressions, psi.node_list)]
    )
    checksum = sum(
        float(np.linalg.norm(action.ravel()[: min(action.size, 1024)]))
        for action in actions
    )
    return {
        "n_lead": 1,
        "n_phonon": 16,
        "n_tree_nodes": len(tree.node_list),
        "model_build_sec": model_build_sec,
        "state_build_sec": state_build_sec,
        "operator_build_sec": operator_build_sec,
        "environment_build_sec": environment_build_sec,
        "expression_build_sec": expression_build_sec,
        "apply_sec": apply_sec,
        "time_total_sec": (
            operator_build_sec
            + environment_build_sec
            + expression_build_sec
            + apply_sec
        ),
        "state_bond_dims": list(psi.bond_dims),
        "operator_bond_dims": list(ttno.bond_dims),
        "state_leaf_shapes": _phonon_leaf_shapes(tree, psi),
        "operator_leaf_shapes": _phonon_leaf_shapes(tree, ttno),
        "state_tensor_elements": int(sum(node.tensor.size for node in psi.node_list)),
        "operator_tensor_elements": int(sum(node.tensor.size for node in ttno.node_list)),
        "checksum": checksum,
        "peak_memory_mb": _peak_memory_mb(),
        "status": "ok",
    }


def run_task(task, snapshot_dir):
    output = snapshot_path(snapshot_dir, task)
    try:
        if task.panel in ("internal_ms", "leaf_d"):
            result = _run_dense_kernel(task)
        elif task.panel == "model_d":
            result = _run_model_kernel(task)
        else:
            raise ValueError(f"unsupported diagnostic panel {task.panel!r}")
        payload = {
            **asdict(task),
            **result,
            "diagnostic_snapshot_version": 1,
        }
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            **asdict(task),
            "diagnostic_snapshot_version": 1,
            "status": f"error: {type(exc).__name__}: {exc}",
        }
        write_snapshot_atomic(output, payload)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    args = parser.parse_args()
    task = read_task(args.manifest, args.task_id)
    output, payload = run_task(task, args.snapshot_dir)
    print(f"Wrote {output}")
    print(json.dumps(payload, sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
