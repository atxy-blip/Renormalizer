#!/usr/bin/env python3
"""Manifest for the Li.W.2024 operator-construction supplementary benchmark."""

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path


CONSTRUCTION_MODE_VALUES = (4, 8, 16, 32, 64, 128, 256)
CONSTRUCTION_STATE_BOND_VALUES = (4, 8, 16, 32, 50, 70, 100)
CONSTRUCTION_PRIMITIVE_BASIS_VALUES = (4, 8, 16, 32, 50, 70, 100)


def uses_primitive_contraction(state_bond: int, primitive_basis: int) -> bool:
    """Return the same adaptive tree rule as the formal Li.W.2024 scan."""

    return int(primitive_basis) > int(state_bond)


@dataclass(frozen=True)
class ConstructionTask:
    task_id: int
    panel: str
    repeat_id: int
    n_modes: int
    state_bond: int
    primitive_basis: int
    contract_primitive: bool

    @property
    def n_total_sites(self):
        return self.n_modes + 1


def construction_tasks(repeats=3):
    """21 parameter points x repeats; mirrors li2024_formal_manifest points."""

    points = []
    points.extend(("modes", n_modes, 20, 10) for n_modes in CONSTRUCTION_MODE_VALUES)
    points.extend(("state_bond", 16, state_bond, 10) for state_bond in CONSTRUCTION_STATE_BOND_VALUES)
    points.extend(("primitive_basis", 16, 20, primitive_basis) for primitive_basis in CONSTRUCTION_PRIMITIVE_BASIS_VALUES)

    tasks = []
    for panel, n_modes, state_bond, primitive_basis in points:
        contract_primitive = uses_primitive_contraction(state_bond, primitive_basis)
        for repeat_id in range(repeats):
            tasks.append(ConstructionTask(
                task_id=len(tasks),
                panel=panel,
                repeat_id=repeat_id,
                n_modes=n_modes,
                state_bond=state_bond,
                primitive_basis=primitive_basis,
                contract_primitive=contract_primitive,
            ))
    return tasks


def write_manifest(path, repeats=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = construction_tasks(repeats=repeats)
    fields = [field.name for field in ConstructionTask.__dataclass_fields__.values()]
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
            return ConstructionTask(
                task_id=int(row["task_id"]),
                panel=row["panel"],
                repeat_id=int(row["repeat_id"]),
                n_modes=int(row["n_modes"]),
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
