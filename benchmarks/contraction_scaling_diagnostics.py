#!/usr/bin/env python3
"""Task manifest and dense-kernel definitions for contraction diagnostics."""

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path

import opt_einsum as oe


MS_VALUES = (10, 20, 30, 50, 70, 100, 150, 220)
D_VALUES = (5, 10, 20, 30, 40, 50, 70, 100)
OPERATOR_BOND = 4


@dataclass(frozen=True)
class DiagnosticTask:
    task_id: int
    panel: str
    kernel: str
    repeat_id: int
    state_bond: int
    primitive_basis: int
    operator_bond: int
    contract_primitive: bool


def diagnostic_tasks(repeats=3):
    controls = []
    controls.extend(
        ("internal_ms", kernel, state_bond, 1, False)
        for kernel in ("sop_internal", "ttno_internal")
        for state_bond in MS_VALUES
    )
    controls.extend(
        ("leaf_d", kernel, 20, primitive_basis, contract_primitive)
        for kernel, contract_primitive in (
            ("ttno_leaf_paired", False),
            ("ttno_leaf_contracted", True),
        )
        for primitive_basis in D_VALUES
    )
    controls.extend(
        ("model_d", kernel, 20, primitive_basis, contract_primitive)
        for kernel, contract_primitive in (
            ("ttno_model_paired", False),
            ("ttno_model_contracted", True),
        )
        for primitive_basis in D_VALUES
    )

    tasks = []
    for panel, kernel, state_bond, primitive_basis, contract_primitive in controls:
        for repeat_id in range(repeats):
            tasks.append(DiagnosticTask(
                task_id=len(tasks),
                panel=panel,
                kernel=kernel,
                repeat_id=repeat_id,
                state_bond=state_bond,
                primitive_basis=primitive_basis,
                operator_bond=OPERATOR_BOND,
                contract_primitive=contract_primitive,
            ))
    return tasks


def kernel_spec(kernel, state_bond, primitive_basis, operator_bond):
    m = int(state_bond)
    d = int(primitive_basis)
    o = int(operator_bond)
    if min(m, d, o) < 1:
        raise ValueError("kernel dimensions must be positive")

    if kernel == "sop_internal":
        return {
            "equation": "Aa,Bb,Cc,abc->ABC",
            "shapes": ((m, m), (m, m), (m, m), (m, m, m)),
            "constant_count": 3,
            "theoretical_power": 4,
            "scaling_variable": "state_bond",
        }
    if kernel == "ttno_internal":
        return {
            "equation": "Axa,Byb,Czc,xyz,abc->ABC",
            "shapes": (
                (m, o, m),
                (m, o, m),
                (m, o, m),
                (o, o, o),
                (m, m, m),
            ),
            "constant_count": 4,
            "theoretical_power": 4,
            "scaling_variable": "state_bond",
        }
    if kernel == "ttno_leaf_paired":
        return {
            "equation": "Axa,xIiJj,aij->AIJ",
            "shapes": ((m, o, m), (o, d, d, d, d), (m, d, d)),
            "constant_count": 2,
            "theoretical_power": 4,
            "scaling_variable": "primitive_basis",
        }
    if kernel == "ttno_leaf_contracted":
        return {
            "equation": "Axa,xIi,ai->AI",
            "shapes": ((m, o, m), (o, d, d), (m, d)),
            "constant_count": 2,
            "theoretical_power": 2,
            "scaling_variable": "primitive_basis",
        }
    raise ValueError(f"unsupported diagnostic kernel {kernel!r}")


def kernel_path_metrics(kernel, state_bond, primitive_basis, operator_bond):
    spec = kernel_spec(kernel, state_bond, primitive_basis, operator_bond)
    path, path_info = oe.contract_path(
        spec["equation"],
        *spec["shapes"],
        shapes=True,
        optimize="optimal",
    )
    return {
        "optimized_flops": int(path_info.opt_cost),
        "largest_intermediate": int(path_info.largest_intermediate),
        "naive_scaling": len(path_info.indices),
        "opt_einsum_max_index_count": int(path_info.scale_list and max(path_info.scale_list) or 0),
        "path": [list(step) for step in path],
        "equation": spec["equation"],
        "operand_shapes": [list(shape) for shape in spec["shapes"]],
        "theoretical_power": spec["theoretical_power"],
        "scaling_variable": spec["scaling_variable"],
    }


def write_manifest(path, repeats=3):
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = diagnostic_tasks(repeats=repeats)
    fieldnames = [field.name for field in DiagnosticTask.__dataclass_fields__.values()]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(asdict(task) for task in tasks)
    return tasks


def read_task(path, task_id):
    with path.open(newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if int(row["task_id"]) != task_id:
                continue
            return DiagnosticTask(
                task_id=int(row["task_id"]),
                panel=row["panel"],
                kernel=row["kernel"],
                repeat_id=int(row["repeat_id"]),
                state_bond=int(row["state_bond"]),
                primitive_basis=int(row["primitive_basis"]),
                operator_bond=int(row["operator_bond"]),
                contract_primitive=row["contract_primitive"].lower() == "true",
            )
    raise KeyError(f"task id {task_id} not found in {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    tasks = write_manifest(args.output, repeats=args.repeats)
    print(f"Wrote {args.output} ({len(tasks)} tasks)")


if __name__ == "__main__":
    main()
