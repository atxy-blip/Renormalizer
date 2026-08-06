import json
from pathlib import Path
import sys
from types import SimpleNamespace

from benchmarks.benchmark_li2024_operator_env import (
    build_li2024_spin_boson_case,
    run_li2024_point,
)
from benchmarks.finalize_li2024_formal import main as finalize_main, missing_task_ids
from benchmarks.li2024_formal_manifest import (
    FORMAL_METHODS,
    MODE_VALUES,
    PRIMITIVE_BASIS_VALUES,
    STATE_BOND_VALUES,
    formal_tasks,
    uses_primitive_contraction,
)
from benchmarks.plot_li2024_operator_scaling import (
    FIT_PANELS_MAIN,
    FIT_PANELS_SI,
    MODE_REFERENCE_POWERS,
    PARAMETER_REFERENCE_POWERS,
    TOPO_SWITCH_X,
    generate,
    summarize,
)
from benchmarks.run_li2024_formal_point import load_snapshot, write_snapshot_atomic
import numpy as np


def _synthetic_row(panel, method, value, time_scale, repeat_id=0):
    n_modes = value if panel == "modes" else 16
    state_bond = value if panel == "state_bond" else 20
    primitive_basis = value if panel == "primitive_basis" else 10
    contracted = primitive_basis > state_bond
    return {
        "status": "ok",
        "case_name": "li2024_spin_boson",
        "quantity": "local_effective_1site_apply_all_nodes",
        "panel": panel,
        "method": method,
        "n_modes": n_modes,
        "target_state_bond": state_bond,
        "primitive_basis_dim": primitive_basis,
        "contract_primitive": contracted,
        "state_max_bond": state_bond,
        "phonon_tree_layout": "primitive_contracted" if contracted else "paired_no_contraction",
        "n_active_nodes": 32 if contracted else 16,
        "n_sop_terms": 1 + 3 * n_modes,
        "ttno_max_bond": 3,
        "state_tensor_elements": 1000,
        "operator_tensor_elements": 2000,
        "repeat_id": repeat_id,
        "time_total_sec": float(value) * time_scale,
        "time_env_build_sec": 0.25 * float(value) * time_scale,
        "time_apply_sec": 0.75 * float(value) * time_scale,
        "relative_error_vs_ttno": 0.0,
    }


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


def test_li2024_main_si_plot_contract():
    assert MODE_REFERENCE_POWERS == {
        "sop_no_env": 3.0,
        "sop_mctdh_like_state_env": 2.0,
        "ttno_with_env": 1.0,
    }
    assert PARAMETER_REFERENCE_POWERS == {
        "state_bond": {method: 4.0 for method in FORMAL_METHODS},
        "primitive_basis": {method: 0.0 for method in FORMAL_METHODS},
    }
    assert [panel.name for panel in FIT_PANELS_MAIN] == ["modes"]
    assert [panel.name for panel in FIT_PANELS_SI] == ["modes", "state_bond", "primitive_basis"]
    assert TOPO_SWITCH_X == {
        "state_bond": 10.0,
        "primitive_basis": 20.0,
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


def test_li2024_si_outputs_keep_parameter_exponents(tmp_path):
    rows = []
    for panel, values in (
        ("modes", (4, 8)),
        ("state_bond", (4, 8)),
        ("primitive_basis", (4, 8)),
    ):
        for method in FORMAL_METHODS:
            for value in values:
                rows.append(_synthetic_row(panel, method, value, 1.0))
    summary, fits, pdf, png = generate(rows, tmp_path / "li2024", figure_mode="si")
    assert {f["panel"] for f in fits} == {"modes", "state_bond", "primitive_basis"}
    assert pdf.name == "li2024_si_scaling_three_panel.pdf"
    assert png.name == "li2024_si_scaling_three_panel.png"


def test_li2024_robustness_panels_keep_method_ranking():
    rows = []
    for panel in ("state_bond", "primitive_basis"):
        for value in (4, 16, 100):
            for method, scale in (
                ("sop_no_env", 100.0),
                ("sop_mctdh_like_state_env", 10.0),
                ("ttno_with_env", 1.0),
            ):
                rows.append(_synthetic_row(panel, method, value, scale))
    summary = summarize(rows)
    by_point = {}
    for row in summary:
        key = (row["panel"], row["target_state_bond"], row["primitive_basis_dim"])
        by_point.setdefault(key, {})[row["method"]] = row["time_total_mean_sec"]
    assert len(by_point) == 6
    for times in by_point.values():
        assert times["ttno_with_env"] < times["sop_mctdh_like_state_env"] < times["sop_no_env"]


def test_li2024_plot_writes_paired_formal_outputs(tmp_path):
    rows = []
    panel_values = {
        "modes": (4, 8),
        "state_bond": (4, 8),
        "primitive_basis": (4, 8),
    }
    for panel, values in panel_values.items():
        for method in FORMAL_METHODS:
            for value in values:
                n_modes = value if panel == "modes" else 16
                state_bond = value if panel == "state_bond" else 20
                primitive_basis = value if panel == "primitive_basis" else 10
                rows.append({
                    "status": "ok",
                    "case_name": "li2024_spin_boson",
                    "quantity": "local_effective_1site_apply_all_nodes",
                    "panel": panel,
                    "method": method,
                    "n_modes": n_modes,
                    "target_state_bond": state_bond,
                    "primitive_basis_dim": primitive_basis,
                    "contract_primitive": primitive_basis > state_bond,
                    "state_max_bond": state_bond,
                    "phonon_tree_layout": "primitive_contracted",
                    "n_active_nodes": n_modes,
                    "n_sop_terms": 1 + 3 * n_modes,
                    "ttno_max_bond": 3,
                    "state_tensor_elements": 1000,
                    "operator_tensor_elements": 2000,
                    "repeat_id": 0,
                    "time_total_sec": float(value),
                    "time_env_build_sec": 0.25 * value,
                    "time_apply_sec": 0.75 * value,
                    "relative_error_vs_ttno": 0.0,
                })

    summary, fits, pdf, png = generate(rows, tmp_path / "li2024")

    assert summary
    assert fits
    assert {f["panel"] for f in fits} == {"modes"}
    assert pdf.name == "li2024_scaling_three_panel.pdf"
    assert png.name == "li2024_scaling_three_panel.png"
    assert pdf.stat().st_size > 0
    assert png.stat().st_size > 0


def test_li2024_finalizer_reports_both_figure_paths(tmp_path, monkeypatch, capsys):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    row = {
        "task_id": 0,
        "status": "ok",
        "case_name": "li2024_spin_boson",
        "quantity": "local_effective_1site_apply_all_nodes",
        "panel": "modes",
        "method": "ttno_with_env",
        "n_modes": 4,
        "target_state_bond": 20,
        "primitive_basis_dim": 10,
        "contract_primitive": False,
        "state_max_bond": 20,
        "phonon_tree_layout": "paired",
        "n_active_nodes": 4,
        "n_sop_terms": 13,
        "ttno_max_bond": 3,
        "state_tensor_elements": 1000,
        "operator_tensor_elements": 2000,
        "repeat_id": 0,
        "time_total_sec": 1.0,
        "time_env_build_sec": 0.25,
        "time_apply_sec": 0.75,
        "relative_error_vs_ttno": 0.0,
    }
    write_snapshot_atomic(snapshot_dir / "point.npz", row)
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text("task_id\n0\n")
    output_prefix = tmp_path / "li2024"
    monkeypatch.setattr(sys, "argv", [
        "finalize_li2024_formal.py",
        "--manifest",
        str(manifest),
        "--snapshot-dir",
        str(snapshot_dir),
        "--raw-output",
        str(tmp_path / "raw.csv"),
        "--missing-output",
        str(tmp_path / "missing.json"),
        "--output-prefix",
        str(output_prefix),
    ])

    finalize_main()

    output = capsys.readouterr().out
    assert "li2024_scaling_three_panel.pdf" in output
    assert "li2024_scaling_three_panel.png" in output
    assert "li2024_si_scaling_three_panel.pdf" in output
    assert "li2024_si_scaling_three_panel.png" in output


def test_li2024_slurm_wrappers_activate_conda_before_nounset():
    scripts = (
        "curie_cpu_li2024_formal_array.sbatch",
        "curie_cpu_li2024_formal_finalize.sbatch",
    )
    for name in scripts:
        text = (Path("benchmarks/scripts") / name).read_text()
        assert text.index("conda activate reno-3.9") < text.index("set -u")
        assert "python -u -m benchmarks." in text
