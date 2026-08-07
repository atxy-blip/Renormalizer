#!/usr/bin/env python3
"""Collect Li.W.2024 formal snapshots and generate the complete three-panel plot."""

import argparse
import csv
import json
from pathlib import Path

from benchmarks.plot_li2024_operator_scaling import generate
from benchmarks.run_li2024_formal_point import load_snapshot


def collect_snapshots(snapshot_dir):
    return [load_snapshot(path) for path in sorted(Path(snapshot_dir).rglob("*.npz"))]


def manifest_task_ids(path):
    with Path(path).open(newline="") as f:
        return {int(row["task_id"]) for row in csv.DictReader(f, delimiter="\t")}


def missing_task_ids(rows, expected_ids):
    ok_ids = {int(row["task_id"]) for row in rows if row.get("status") == "ok"}
    return sorted(set(expected_ids) - ok_ids)


def write_raw(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="") as f:
        if not fields:
            return
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({
            key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
            for key, value in row.items()
        } for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--missing-output", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--figures-dir", type=Path, default=None)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()

    rows = collect_snapshots(args.snapshot_dir)
    expected = manifest_task_ids(args.manifest)
    missing = missing_task_ids(rows, expected)
    errors = [
        {"task_id": row.get("task_id"), "status": row.get("status")}
        for row in rows
        if row.get("status") != "ok"
    ]
    write_raw(args.raw_output, rows)
    args.missing_output.parent.mkdir(parents=True, exist_ok=True)
    args.missing_output.write_text(json.dumps({
        "expected_tasks": len(expected),
        "available_snapshots": len(rows),
        "missing_or_error_task_ids": missing,
        "errors": errors,
    }, indent=2, sort_keys=True) + "\n")

    if missing and not args.allow_partial:
        raise RuntimeError(
            f"refusing to label incomplete result as final: {len(missing)} missing/error tasks"
        )
    summary, fits, pdf, png = generate(
        rows, args.output_prefix, figure_mode="main", figures_dir=args.figures_dir
    )
    summary, si_fits, si_pdf, si_png = generate(
        rows, args.output_prefix, figure_mode="si", figures_dir=args.figures_dir
    )
    print(
        f"Collected {len(rows)}/{len(expected)} snapshots; "
        f"wrote {len(summary)} summary rows, {len(fits)} main fits, {len(si_fits)} SI fits, "
        f"and figures {pdf}, {png}, {si_pdf}, {si_png}"
    )


if __name__ == "__main__":
    main()
