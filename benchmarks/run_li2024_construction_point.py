#!/usr/bin/env python3
"""Run one Li.W.2024 operator-construction supplementary task."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from benchmarks.benchmark_adaptive_operator_env import _time_and_memory
from benchmarks.benchmark_li2024_operator_env import build_li2024_spin_boson_case
from benchmarks.li2024_construction_manifest import read_task
from renormalizer.tn import SOPBaselineOperator, TTNO


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
        / f"task_{task.task_id:04d}_repeat_{task.repeat_id}.npz"
    )


def run_construction_task(task, timeout_sec=1800, memory_limit_mb=120000):
    tree, terms, _psi = build_li2024_spin_boson_case(
        n_modes=task.n_modes,
        state_bond=task.state_bond,
        primitive_basis=task.primitive_basis,
        contract_primitive=task.contract_primitive,
    )
    sop, sop_time, sop_mem, sop_status = _time_and_memory(
        lambda: SOPBaselineOperator.from_symbolic_terms(terms, tree), timeout_sec
    )
    ttno, ttno_time, ttno_mem, ttno_status = _time_and_memory(
        lambda: TTNO(tree, terms), timeout_sec
    )
    if sop_status != "ok" or ttno_status != "ok":
        status = f"sop={sop_status}; ttno={ttno_status}"
    elif memory_limit_mb > 0 and max(sop_mem, ttno_mem) > memory_limit_mb:
        status = (
            f"memory_limit_exceeded: {max(sop_mem, ttno_mem):.1f} MB "
            f"> {memory_limit_mb:.1f} MB"
        )
    else:
        status = "ok"

    ttno_max_bond = None
    ttno_mean_bond = None
    operator_tensor_elements = None
    if ttno is not None:
        ttno_max_bond = max(ttno.bond_dims)
        ttno_mean_bond = float(np.mean(ttno.bond_dims))
        operator_tensor_elements = int(sum(node.tensor.size for node in ttno.node_list))

    return {
        **asdict(task),
        "n_sop_terms": len(terms),
        "sop_build_time_sec": sop_time,
        "sop_peak_memory_mb": sop_mem,
        "ttno_build_time_sec": ttno_time,
        "ttno_peak_memory_mb": ttno_mem,
        "ttno_max_bond": ttno_max_bond,
        "ttno_mean_bond": ttno_mean_bond,
        "operator_tensor_elements": operator_tensor_elements,
        "status": status,
    }


def run_task(task, snapshot_dir, timeout_sec, memory_limit_mb):
    output = snapshot_path(snapshot_dir, task)
    try:
        payload = run_construction_task(task, timeout_sec, memory_limit_mb)
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            **asdict(task),
            "status": f"error: {type(exc).__name__}: {exc}",
        }
        write_snapshot_atomic(output, payload)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=3600)
    parser.add_argument("--memory-limit-mb", type=float, default=120000)
    args = parser.parse_args()
    task = read_task(args.manifest, args.task_id)
    output, payload = run_task(task, args.snapshot_dir, args.timeout_sec, args.memory_limit_mb)
    print(f"Wrote {output}")
    print(json.dumps(payload, sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
