#!/usr/bin/env python3
"""Run one recoverable Li.W.2024 spin--boson operator benchmark task."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from benchmarks.benchmark_li2024_operator_env import run_li2024_point
from benchmarks.li2024_formal_manifest import FORMAL_METHODS, read_task


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
        / task.method
        / f"task_{task.task_id:04d}_repeat_{task.repeat_id}.npz"
    )


def run_task(task, snapshot_dir, timeout_sec, memory_limit_mb):
    if task.method not in FORMAL_METHODS:
        raise ValueError(f"unsupported formal method {task.method!r}")
    output = snapshot_path(snapshot_dir, task)
    args = SimpleNamespace(
        timeout_sec=timeout_sec,
        memory_limit_mb=memory_limit_mb,
        active_scope="all_nodes",
    )
    try:
        rows = run_li2024_point(
            panel=task.panel,
            n_modes=task.n_modes,
            state_bond=task.state_bond,
            primitive_basis=task.primitive_basis,
            contract_primitive=task.contract_primitive,
            repeat_id=task.repeat_id,
            args=args,
            git_commit="li2024-formal",
            selected_methods=(task.method,),
        )
        if len(rows) != 1:
            raise RuntimeError(f"expected one method row, got {len(rows)}")
        payload = {**asdict(task), **rows[0], "li2024_snapshot_version": 1}
        write_snapshot_atomic(output, payload)
        return output, payload
    except BaseException as exc:
        payload = {
            **asdict(task),
            "li2024_snapshot_version": 1,
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
