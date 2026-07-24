import json
import math
from pathlib import Path

from benchmarks.benchmark_adaptive_operator_env import build_hubbard_junction_case
from benchmarks.contraction_scaling_diagnostics import (
    diagnostic_tasks,
    kernel_path_metrics,
)
from benchmarks.run_contraction_scaling_diagnostic import (
    load_snapshot,
    write_snapshot_atomic,
)
from benchmarks.summarize_contraction_scaling_diagnostics import (
    fit_scaling,
    summarize_repeats,
)
from renormalizer.mps.backend import np


def _local_log_slope(x1, y1, x2, y2):
    return math.log(y2 / y1) / math.log(x2 / x1)


def test_diagnostic_manifest_covers_kernel_and_model_controls():
    tasks = diagnostic_tasks(repeats=3)

    assert len(tasks) == (2 * 8 + 2 * 8 + 2 * 8) * 3
    assert [task.task_id for task in tasks] == list(range(len(tasks)))

    assert {
        (task.panel, task.kernel, task.contract_primitive)
        for task in tasks
    } == {
        ("internal_ms", "sop_internal", False),
        ("internal_ms", "ttno_internal", False),
        ("leaf_d", "ttno_leaf_paired", False),
        ("leaf_d", "ttno_leaf_contracted", True),
        ("model_d", "ttno_model_paired", False),
        ("model_d", "ttno_model_contracted", True),
    }


def test_shape_only_path_metrics_distinguish_ms4_d4_and_d2():
    sop_16 = kernel_path_metrics("sop_internal", state_bond=16, primitive_basis=1, operator_bond=4)
    sop_32 = kernel_path_metrics("sop_internal", state_bond=32, primitive_basis=1, operator_bond=4)
    ttno_16 = kernel_path_metrics("ttno_internal", state_bond=16, primitive_basis=1, operator_bond=4)
    ttno_32 = kernel_path_metrics("ttno_internal", state_bond=32, primitive_basis=1, operator_bond=4)

    sop_ms_slope = _local_log_slope(16, sop_16["optimized_flops"], 32, sop_32["optimized_flops"])
    ttno_ms_slope = _local_log_slope(16, ttno_16["optimized_flops"], 32, ttno_32["optimized_flops"])
    assert 3.8 < sop_ms_slope <= 4.05
    assert 3.7 < ttno_ms_slope <= 4.05

    paired_50 = kernel_path_metrics("ttno_leaf_paired", state_bond=20, primitive_basis=50, operator_bond=4)
    paired_100 = kernel_path_metrics("ttno_leaf_paired", state_bond=20, primitive_basis=100, operator_bond=4)
    contracted_50 = kernel_path_metrics("ttno_leaf_contracted", state_bond=20, primitive_basis=50, operator_bond=4)
    contracted_100 = kernel_path_metrics("ttno_leaf_contracted", state_bond=20, primitive_basis=100, operator_bond=4)

    paired_d_slope = _local_log_slope(50, paired_50["optimized_flops"], 100, paired_100["optimized_flops"])
    contracted_d_slope = _local_log_slope(
        50,
        contracted_50["optimized_flops"],
        100,
        contracted_100["optimized_flops"],
    )
    assert 3.8 < paired_d_slope <= 4.05
    assert 1.5 < contracted_d_slope < 2.1


def test_hubbard_builder_can_switch_phonon_primitive_contraction():
    paired_tree, _, _ = build_hubbard_junction_case(
        n_lead=1,
        n_phonon=4,
        force_phonon_basis=6,
        phonon_contract_primitive=False,
    )
    contracted_tree, _, _ = build_hubbard_junction_case(
        n_lead=1,
        n_phonon=4,
        force_phonon_basis=6,
        phonon_contract_primitive=True,
    )

    def sho_counts_per_node(tree):
        return sorted(
            sum(basis.__class__.__name__ == "BasisSHO" for basis in node.basis_sets)
            for node in tree.node_list
            if any(basis.__class__.__name__ == "BasisSHO" for basis in node.basis_sets)
        )

    assert sho_counts_per_node(paired_tree) == [2, 2]
    assert sho_counts_per_node(contracted_tree) == [1, 1, 1, 1]


def test_diagnostic_snapshot_is_atomic_json_without_pickle(tmp_path):
    path = tmp_path / "point.npz"
    payload = {
        "panel": "internal_ms",
        "kernel": "ttno_internal",
        "optimized_flops": 12345,
        "status": "ok",
    }

    write_snapshot_atomic(path, payload)

    with np.load(path, allow_pickle=False) as data:
        assert json.loads(str(data["payload_json"])) == payload
    assert load_snapshot(path) == payload


def test_diagnostic_summary_uses_repeat_medians_and_fits_log_slope():
    rows = []
    for d in (10, 20, 40, 80):
        for repeat_id, multiplier in enumerate((0.9, 1.0, 20.0)):
            rows.append({
                "panel": "leaf_d",
                "kernel": "ttno_leaf_paired",
                "state_bond": 20,
                "primitive_basis": d,
                "operator_bond": 4,
                "contract_primitive": False,
                "repeat_id": repeat_id,
                "status": "ok",
                "optimized_flops": 3 * d ** 4,
                "apply_sec": multiplier * d ** 4,
            })

    summary = summarize_repeats(rows)
    fits = fit_scaling(summary)

    assert len(summary) == 4
    assert summary[0]["apply_sec_median"] == 10 ** 4
    assert next(row for row in fits if row["metric"] == "optimized_flops")["alpha"] == 4.0
    assert next(row for row in fits if row["metric"] == "apply_sec")["alpha"] == 4.0


def test_slurm_wrappers_enable_nounset_only_after_conda_activation():
    scripts = (
        "curie_cpu_contraction_scaling_diagnostics.sbatch",
        "curie_cpu_contraction_scaling_summary.sbatch",
    )
    for name in scripts:
        text = (Path("benchmarks/scripts") / name).read_text()
        assert text.index("conda activate reno-3.9") < text.index("set -u")
