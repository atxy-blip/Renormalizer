import json

import numpy as np

from benchmarks.benchmark_adaptive_operator_env import (
    _fit_one,
    _run_point,
)
from benchmarks.ren_formal_manifest import FORMAL_METHODS, formal_tasks


def test_formal_tasks_match_ren_parameter_controls():
    tasks = formal_tasks(repeats=3)

    assert len(tasks) == (7 + 9 + 8) * len(FORMAL_METHODS) * 3
    assert [task.task_id for task in tasks] == list(range(len(tasks)))

    modes = [task for task in tasks if task.panel == "modes" and task.method == "ttno_with_env" and task.repeat_id == 0]
    assert [(task.n_phonon, task.n_total_sites) for task in modes] == [
        (12, 18), (24, 30), (40, 46), (68, 74), (112, 118), (180, 186), (294, 300),
    ]
    assert {(task.state_bond, task.primitive_basis) for task in modes} == {(20, 10)}

    bonds = [task for task in tasks if task.panel == "state_bond" and task.method == "ttno_with_env" and task.repeat_id == 0]
    assert [task.state_bond for task in bonds] == [10, 20, 30, 50, 70, 100, 150, 220, 300]
    assert {(task.n_phonon, task.primitive_basis) for task in bonds} == {(16, 10)}

    bases = [task for task in tasks if task.panel == "primitive_basis" and task.method == "ttno_with_env" and task.repeat_id == 0]
    assert [task.primitive_basis for task in bases] == [5, 10, 20, 30, 40, 50, 70, 100]
    assert {(task.n_phonon, task.state_bond) for task in bases} == {(16, 20)}


def test_snapshot_payload_is_json_without_pickle(tmp_path):
    from benchmarks.run_ren_formal_point import load_snapshot, write_snapshot_atomic

    path = tmp_path / "point.npz"
    payload = {"method": "ttno_with_env", "time_total_sec": 1.25, "status": "ok"}
    write_snapshot_atomic(path, payload)

    with np.load(path, allow_pickle=False) as data:
        assert json.loads(str(data["payload_json"])) == payload
    assert load_snapshot(path) == payload


def test_single_point_can_select_one_formal_method():
    from types import SimpleNamespace

    args = SimpleNamespace(
        timeout_sec=120,
        memory_limit_mb=0.0,
        max_phonon_basis=10,
        active_scope="all_nodes",
    )
    rows = _run_point(
        "state_bond",
        1,
        0,
        0,
        args,
        "test",
        state_bond_dim=1,
        primitive_basis_dim=None,
        selected_methods=("sop_mctdh_like_state_env",),
    )

    assert [row["method"] for row in rows] == ["sop_mctdh_like_state_env"]
    assert rows[0]["status"] == "ok"
    assert rows[0]["relative_error_vs_ttno"] < 1e-12


def test_fit_rejects_repeated_single_x_value():
    rows = [
        {
            "status": "ok",
            "method": "ttno_with_env",
            "scaling_path": "primitive_basis",
            "n_total_sites": 22,
            "n_lead": 1,
            "n_phonon": 16,
            "time_total_sec": elapsed,
        }
        for elapsed in (1.0, 1.1, 0.9)
    ]

    fit = _fit_one(rows, "ttno_with_env", "primitive_basis", "n_total_sites", "all_ok", 0.25)

    assert np.isnan(fit["alpha"])
    assert fit["n_points_used"] == 3
