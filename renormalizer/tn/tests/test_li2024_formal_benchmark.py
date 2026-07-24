import json
from pathlib import Path
from types import SimpleNamespace

from benchmarks.benchmark_li2024_operator_env import (
    build_li2024_spin_boson_case,
    run_li2024_point,
)
from benchmarks.finalize_li2024_formal import missing_task_ids
from benchmarks.li2024_formal_manifest import (
    FORMAL_METHODS,
    MODE_VALUES,
    PRIMITIVE_BASIS_VALUES,
    STATE_BOND_VALUES,
    formal_tasks,
    uses_primitive_contraction,
)
from benchmarks.plot_li2024_operator_scaling import REFERENCE_POWERS, summarize
from benchmarks.run_li2024_formal_point import load_snapshot, write_snapshot_atomic
import numpy as np


def test_manifest_matches_li2024_binary_controls_and_adaptive_topology():
    tasks = formal_tasks(repeats=3)

    assert MODE_VALUES == (4, 8, 16, 32, 64, 128, 256)
    assert STATE_BOND_VALUES == (4, 8, 16, 32, 50, 70, 100)
    assert PRIMITIVE_BASIS_VALUES == (4, 8, 16, 32, 50, 70, 100)
    assert len(tasks) == (7 + 7 + 7) * len(FORMAL_METHODS) * 3 == 189
    assert [task.task_id for task in tasks] == list(range(189))

    modes = [
        task for task in tasks
        if task.panel == "modes"
        and task.method == "ttno_with_env"
        and task.repeat_id == 0
    ]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in modes] == [
        (n_modes, 20, 10) for n_modes in MODE_VALUES
    ]
    assert {task.contract_primitive for task in modes} == {False}

    bonds = [
        task for task in tasks
        if task.panel == "state_bond"
        and task.method == "ttno_with_env"
        and task.repeat_id == 0
    ]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in bonds] == [
        (16, state_bond, 10) for state_bond in STATE_BOND_VALUES
    ]
    assert [task.contract_primitive for task in bonds] == [
        state_bond < 10 for state_bond in STATE_BOND_VALUES
    ]

    bases = [
        task for task in tasks
        if task.panel == "primitive_basis"
        and task.method == "ttno_with_env"
        and task.repeat_id == 0
    ]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in bases] == [
        (16, 20, primitive_basis) for primitive_basis in PRIMITIVE_BASIS_VALUES
    ]
    assert [task.contract_primitive for task in bases] == [
        primitive_basis > 20 for primitive_basis in PRIMITIVE_BASIS_VALUES
    ]

    assert uses_primitive_contraction(state_bond=20, primitive_basis=21)
    assert not uses_primitive_contraction(state_bond=20, primitive_basis=20)


def test_spin_boson_builder_switches_only_the_phonon_leaf_factorization():
    paired_tree, paired_terms, paired_psi = build_li2024_spin_boson_case(
        n_modes=4,
        state_bond=3,
        primitive_basis=2,
        contract_primitive=False,
    )
    contracted_tree, contracted_terms, contracted_psi = build_li2024_spin_boson_case(
        n_modes=4,
        state_bond=3,
        primitive_basis=6,
        contract_primitive=True,
    )

    def sho_counts(tree):
        return sorted(
            sum(basis.__class__.__name__ == "BasisSHO" for basis in node.basis_sets)
            for node in tree.node_list
            if any(basis.__class__.__name__ == "BasisSHO" for basis in node.basis_sets)
        )

    assert sho_counts(paired_tree) == [2, 2]
    assert sho_counts(contracted_tree) == [1, 1, 1, 1]
    assert len(paired_terms) == len(contracted_terms) == 1 + 3 * 4
    assert max(paired_psi.bond_dims) == max(contracted_psi.bond_dims) == 3


def test_small_li2024_point_records_topology_and_matches_ttno_reference():
    args = SimpleNamespace(
        active_scope="all_nodes",
        timeout_sec=120,
        memory_limit_mb=0.0,
    )
    rows = run_li2024_point(
        panel="primitive_basis",
        n_modes=4,
        state_bond=2,
        primitive_basis=3,
        contract_primitive=True,
        repeat_id=0,
        args=args,
        git_commit="test",
        selected_methods=("sop_mctdh_like_state_env",),
    )

    assert len(rows) == 1
    assert rows[0]["case_name"] == "li2024_spin_boson"
    assert rows[0]["contract_primitive"] is True
    assert rows[0]["phonon_tree_layout"] == "primitive_contracted"
    assert rows[0]["target_state_bond"] == 2
    assert rows[0]["primitive_basis_dim"] == 3
    assert rows[0]["status"] == "ok"
    assert rows[0]["relative_error_vs_ttno"] < 1e-12


def test_snapshot_round_trip_and_missing_task_detection(tmp_path):
    path = tmp_path / "point.npz"
    payload = {
        "task_id": 3,
        "panel": "modes",
        "method": "ttno_with_env",
        "contract_primitive": False,
        "status": "ok",
    }
    write_snapshot_atomic(path, payload)

    with np.load(path, allow_pickle=False) as data:
        assert json.loads(str(data["payload_json"])) == payload
    assert load_snapshot(path) == payload
    assert missing_task_ids([payload], expected_ids={1, 2, 3}) == [1, 2]


def test_li2024_plot_guides_match_binary_tree_mathematics():
    assert REFERENCE_POWERS["modes"] == {
        "sop_no_env": 3.0,
        "sop_mctdh_like_state_env": 2.0,
        "ttno_with_env": 1.0,
    }
    assert REFERENCE_POWERS["state_bond"] == {
        method: 4.0 for method in FORMAL_METHODS
    }
    assert REFERENCE_POWERS["primitive_basis"] == {
        method: 0.0 for method in FORMAL_METHODS
    }

    rows = []
    for repeat_id, elapsed in enumerate((3.0, 5.0, 7.0)):
        rows.append({
            "status": "ok",
            "panel": "primitive_basis",
            "method": "ttno_with_env",
            "n_modes": 16,
            "target_state_bond": 20,
            "primitive_basis_dim": 32,
            "contract_primitive": True,
            "state_max_bond": 20,
            "phonon_tree_layout": "primitive_contracted",
            "n_active_nodes": 32,
            "n_sop_terms": 49,
            "ttno_max_bond": 3,
            "state_tensor_elements": 1000,
            "operator_tensor_elements": 2000,
            "repeat_id": repeat_id,
            "time_total_sec": elapsed,
            "time_env_build_sec": 1.0,
            "time_apply_sec": elapsed - 1.0,
            "relative_error_vs_ttno": 0.0,
        })
    summary = summarize(rows)
    assert len(summary) == 1
    assert summary[0]["time_total_mean_sec"] == 5.0
    assert summary[0]["n_repeats"] == 3
    assert summary[0]["contract_primitive"] is True


def test_li2024_slurm_wrappers_activate_conda_before_nounset():
    scripts = (
        "curie_cpu_li2024_formal_array.sbatch",
        "curie_cpu_li2024_formal_finalize.sbatch",
    )
    for name in scripts:
        text = (Path("benchmarks/scripts") / name).read_text()
        assert text.index("conda activate reno-3.9") < text.index("set -u")
        assert "python -u -m benchmarks." in text
