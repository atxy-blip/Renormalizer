from dataclasses import asdict

import numpy as np

from benchmarks.analyze_li2024_stage_breakdown import (
    ALL_METRICS,
    FORMAL_METHODS,
    compute_fits,
    generate as generate_stage,
    summarize_modes,
)
from benchmarks.finalize_li2024_construction import generate as generate_construction
from benchmarks.li2024_construction_manifest import (
    CONSTRUCTION_MODE_VALUES,
    CONSTRUCTION_PRIMITIVE_BASIS_VALUES,
    CONSTRUCTION_STATE_BOND_VALUES,
    construction_tasks,
    read_task,
    uses_primitive_contraction,
    write_manifest,
)
from benchmarks.run_li2024_construction_point import (
    load_snapshot,
    run_construction_task,
    write_snapshot_atomic,
)


def test_construction_manifest_matches_li2024_points():
    tasks = construction_tasks(repeats=3)
    assert len(tasks) == (7 + 7 + 7) * 3 == 63
    assert [task.task_id for task in tasks] == list(range(63))

    modes = [task for task in tasks if task.panel == "modes" and task.repeat_id == 0]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in modes] == [
        (n_modes, 20, 10) for n_modes in CONSTRUCTION_MODE_VALUES
    ]
    bonds = [task for task in tasks if task.panel == "state_bond" and task.repeat_id == 0]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in bonds] == [
        (16, state_bond, 10) for state_bond in CONSTRUCTION_STATE_BOND_VALUES
    ]
    bases = [task for task in tasks if task.panel == "primitive_basis" and task.repeat_id == 0]
    assert [(task.n_modes, task.state_bond, task.primitive_basis) for task in bases] == [
        (16, 20, primitive_basis) for primitive_basis in CONSTRUCTION_PRIMITIVE_BASIS_VALUES
    ]
    assert uses_primitive_contraction(state_bond=20, primitive_basis=21)
    assert not uses_primitive_contraction(state_bond=20, primitive_basis=20)


def test_construction_manifest_round_trip(tmp_path):
    path = tmp_path / "manifest.tsv"
    write_manifest(path, repeats=3)
    task = read_task(path, 7)
    assert task.panel == "modes"
    assert task.n_modes == 16
    assert task.repeat_id == 1


def test_construction_snapshot_round_trip(tmp_path):
    path = tmp_path / "point.npz"
    payload = {"task_id": 0, "status": "ok", "sop_build_time_sec": 0.1}
    write_snapshot_atomic(path, payload)
    assert load_snapshot(path) == payload


def test_construction_task_small_smoke():
    from benchmarks.li2024_construction_manifest import ConstructionTask

    task = ConstructionTask(
        task_id=0,
        panel="modes",
        repeat_id=0,
        n_modes=2,
        state_bond=2,
        primitive_basis=2,
        contract_primitive=False,
    )
    payload = run_construction_task(task, timeout_sec=120, memory_limit_mb=4096)
    assert payload["status"] == "ok"
    assert payload["sop_build_time_sec"] >= 0
    assert payload["ttno_build_time_sec"] >= 0
    assert payload["operator_tensor_elements"] > 0
    assert payload["ttno_max_bond"] >= 1


def _stage_row(method, n_modes, scale):
    return {
        "status": "ok",
        "panel": "modes",
        "method": method,
        "n_modes": n_modes,
        "n_active_nodes": 2 * n_modes,
        "n_sop_terms": 1 + 3 * n_modes,
        "state_tensor_elements": 1000 * n_modes,
        "time_total_sec": 10.0 * scale * n_modes**3,
        "time_env_build_sec": 4.0 * scale * n_modes**2,
        "time_apply_sec": 6.0 * scale * n_modes**3,
        "memory_peak_mb": 10.0 * n_modes,
        "repeat_id": 0,
    }


def _stage_rows():
    rows = []
    scales = {
        "sop_no_env": 1.0,
        "sop_mctdh_like_state_env": 0.5,
        "ttno_with_env": 0.1,
    }
    for method in FORMAL_METHODS:
        for n_modes in (4, 8, 16, 32, 64, 128, 256):
            rows.append(_stage_row(method, n_modes, scales[method]))
    return rows


def test_stage_breakdown_summary_and_fits():
    rows = _stage_rows()
    summary = summarize_modes(rows)
    assert len(summary) == len(FORMAL_METHODS) * 7
    for row in summary:
        assert row["time_total_mean_sec"] > 0
        assert row["elements_per_apply_second"] > 0

    fits = compute_fits(summary)
    assert len(fits) == len(FORMAL_METHODS) * len(ALL_METRICS)
    for fit in fits:
        assert fit["fit_window"] == "largest_four"
        assert fit["r2"] > 0.99


def test_stage_breakdown_artifacts(tmp_path):
    summary, fits, pdf, png = generate_stage(_stage_rows(), tmp_path / "li2024")
    assert summary
    assert fits
    assert pdf.name == "li2024_stage_breakdown.pdf"
    assert png.name == "li2024_stage_breakdown.png"
    assert pdf.stat().st_size > 0
    assert png.stat().st_size > 0


def test_construction_finalizer_accepts_ok_rows(tmp_path):
    rows = []
    for task in construction_tasks(repeats=3):
        rows.append({
            **asdict(task),
            "n_sop_terms": 1 + 3 * task.n_modes,
            "sop_build_time_sec": 0.1,
            "sop_peak_memory_mb": 1.0,
            "ttno_build_time_sec": 0.2,
            "ttno_peak_memory_mb": 2.0,
            "ttno_max_bond": 3,
            "ttno_mean_bond": 2.0,
            "operator_tensor_elements": 1000,
            "status": "ok",
        })
    summary, fits, pdf, png = generate_construction(rows, tmp_path / "li2024")
    assert len(summary) == 21
    assert len(fits) == 2 * 3
    assert pdf.name == "li2024_construction_scaling.pdf"
    assert png.name == "li2024_construction_scaling.png"
