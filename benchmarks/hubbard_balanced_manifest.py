#!/usr/bin/env python3
"""Manifest for the Hubbard-junction balanced lead/phonon supplementary scan."""

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path


BALANCED_PAIRS = ((4, 1), (8, 2), (16, 4), (32, 8), (64, 16))
HUBBARD_STATE_BOND = 20
HUBBARD_PRIMITIVE_BASIS = 10


@dataclass(frozen=True)
class HubbardBalancedTask:
    task_id: int
    panel: str
    method: str
    repeat_id: int
    n_lead: int
    n_phonon: int
    state_bond: int
    primitive_basis: int
    contract_primitive: bool

    @property
    def n_total_sites(self):
        return 4 * self.n_lead + 2 + self.n_phonon


def hubbard_balanced_tasks(repeats=3, methods=("sop_no_env", "sop_mctdh_like_state_env", "ttno_with_env")):
    tasks = []
    for n_lead, n_phonon in BALANCED_PAIRS:
        for method in methods:
            for repeat_id in range(repeats):
                tasks.append(HubbardBalancedTask(
                    task_id=len(tasks),
                    panel="balanced",
                    method=method,
                    repeat_id=repeat_id,
                    n_lead=n_lead,
                    n_phonon=n_phonon,
                    state_bond=HUBBARD_STATE_BOND,
                    primitive_basis=HUBBARD_PRIMITIVE_BASIS,
                    contract_primitive=HUBBARD_PRIMITIVE_BASIS > HUBBARD_STATE_BOND,
                ))
    return tasks


def write_manifest(path, repeats=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = hubbard_balanced_tasks(repeats=repeats)
    fields = [field.name for field in HubbardBalancedTask.__dataclass_fields__.values()]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(asdict(task) for task in tasks)
    return tasks


def read_task(path, task_id):
    with path.open(newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if int(row["task_id"]) != int(task_id):
                continue
            return HubbardBalancedTask(
                task_id=int(row["task_id"]),
                panel=row["panel"],
                method=row["method"],
                repeat_id=int(row["repeat_id"]),
                n_lead=int(row["n_lead"]),
                n_phonon=int(row["n_phonon"]),
                state_bond=int(row["state_bond"]),
                primitive_basis=int(row["primitive_basis"]),
                contract_primitive=row["contract_primitive"].lower() == "true",
            )
    raise KeyError(f"task_id {task_id} not found in {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    tasks = write_manifest(args.output, repeats=args.repeats)
    print(f"Wrote {args.output} ({len(tasks)} tasks)")


if __name__ == "__main__":
    main()
