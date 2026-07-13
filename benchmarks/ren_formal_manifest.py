#!/usr/bin/env python3
"""Generate the independent tasks for the Ren-style formal Tree benchmark."""

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path


FORMAL_METHODS = (
    "sop_no_env",
    "sop_mctdh_like_state_env",
    "ttno_with_env",
)

MODES_PHONON_VALUES = (12, 24, 40, 68, 112, 180, 294)
STATE_BOND_VALUES = (10, 20, 30, 50, 70, 100, 150, 220, 300)
PRIMITIVE_BASIS_VALUES = (5, 10, 20, 30, 40, 50, 70, 100)


@dataclass(frozen=True)
class FormalTask:
    task_id: int
    panel: str
    method: str
    repeat_id: int
    n_lead: int
    n_phonon: int
    state_bond: int
    primitive_basis: int

    @property
    def n_total_sites(self):
        return 4 * self.n_lead + 2 + self.n_phonon


def formal_tasks(repeats=3):
    points = []
    points.extend(("modes", 1, n_phonon, 20, 10) for n_phonon in MODES_PHONON_VALUES)
    points.extend(("state_bond", 1, 16, state_bond, 10) for state_bond in STATE_BOND_VALUES)
    points.extend(("primitive_basis", 1, 16, 20, primitive_basis) for primitive_basis in PRIMITIVE_BASIS_VALUES)

    tasks = []
    for panel, n_lead, n_phonon, state_bond, primitive_basis in points:
        for method in FORMAL_METHODS:
            for repeat_id in range(repeats):
                tasks.append(FormalTask(
                    task_id=len(tasks),
                    panel=panel,
                    method=method,
                    repeat_id=repeat_id,
                    n_lead=n_lead,
                    n_phonon=n_phonon,
                    state_bond=state_bond,
                    primitive_basis=primitive_basis,
                ))
    return tasks


def write_manifest(path, repeats=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [field.name for field in FormalTask.__dataclass_fields__.values()]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(asdict(task) for task in formal_tasks(repeats))


def read_task(path, task_id):
    with path.open(newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if int(row["task_id"]) == task_id:
                return FormalTask(**{
                    key: value if key in ("panel", "method") else int(value)
                    for key, value in row.items()
                })
    raise KeyError(f"task_id {task_id} not found in {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    write_manifest(args.output, args.repeats)
    print(f"Wrote {args.output} ({len(formal_tasks(args.repeats))} tasks)")


if __name__ == "__main__":
    main()
