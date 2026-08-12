#!/usr/bin/env python3
"""Manifest for the Hubbard-junction per-node profiling supplement."""

import argparse
from pathlib import Path


PERNODE_POINTS = ((8, 2), (16, 4))
HUBBARD_STATE_BOND = 20
HUBBARD_PRIMITIVE_BASIS = 10


def point_for_task(task_id):
    return PERNODE_POINTS[int(task_id)]


def write_manifest(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write("task_id\tn_lead\tn_phonon\n")
        for task_id, (n_lead, n_phonon) in enumerate(PERNODE_POINTS):
            f.write(f"{task_id}\t{n_lead}\t{n_phonon}\n")
    return PERNODE_POINTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    points = write_manifest(args.output)
    print(f"Wrote {args.output} ({len(points)} tasks)")


if __name__ == "__main__":
    main()
