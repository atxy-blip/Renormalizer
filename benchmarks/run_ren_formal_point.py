#!/usr/bin/env python3
"""Run one formal Tree benchmark task and atomically save an NPZ snapshot."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from benchmarks.benchmark_adaptive_operator_env import _run_point
from benchmarks.ren_formal_manifest import FORMAL_METHODS, read_task
import numpy as np


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
    return snapshot_dir / task.panel / task.method / f"task_{task.task_id:04d}_repeat_{task.repeat_id}.npz"


def run_task(task, snapshot_dir, timeout_sec, memory_limit_mb):
    if task.method not in FORMAL_METHODS:
        raise ValueError(f"unsupported formal method {task.method!r}")
    output = snapshot_path(snapshot_dir, task)
    args = SimpleNamespace(
        timeout_sec=timeout_sec,
        memory_limit_mb=memory_limit_mb,
        max_phonon_basis=task.primitive_basis,
        active_scope="all_nodes",
    )
    try:
        rows = _run_point(
            task.panel,
            task.n_lead,
            task.n_phonon,
            task.repeat_id,
            args,
            "formal",
            state_bond_dim=task.state_bond,
            primitive_basis_dim=task.primitive_basis,
            selected_methods=(task.method,),
        )
        if len(rows) != 1:
            raise RuntimeError(f"expected one method row, got {len(rows)}")
        payload = {**asdict(task), **rows[0], "formal_snapshot_version": 1}
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            **asdict(task),
            "formal_snapshot_version": 1,
            "status": f"error: {type(exc).__name__}: {exc}",
        }
        write_snapshot_atomic(output, payload)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--timeout-sec", type=int, default=250000)
    parser.add_argument("--memory-limit-mb", type=float, default=120000)
    args = parser.parse_args()
    task = read_task(args.manifest, args.task_id)
    output, payload = run_task(task, args.snapshot_dir, args.timeout_sec, args.memory_limit_mb)
    print(f"Wrote {output}")
    print(json.dumps(payload, sort_keys=True, default=_json_default))


if __name__ == "__main__":
    main()
