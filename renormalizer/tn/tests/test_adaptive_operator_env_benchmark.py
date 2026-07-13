import csv
import math
from types import SimpleNamespace

import pytest

import benchmarks.benchmark_adaptive_operator_env as benchmark_module

from benchmarks.benchmark_adaptive_operator_env import (
    RAW_FIELDS,
    SOPOneSiteEffective,
    _scaling_points,
    _run_point,
    build_hubbard_junction_case,
    run_benchmark,
)
from renormalizer.mps.backend import np
from renormalizer.tn import SOPBaselineOperator


def test_sop_one_site_strict_term_cache_does_not_share_operator_signatures():
    tree, terms, psi = build_hubbard_junction_case(n_lead=2, n_phonon=0)
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)

    signature_applier = SOPOneSiteEffective(sop, psi, psi.root)
    signature_applier.build_env_cache(cache_mode="signature")
    signature_action = signature_applier.apply(cache_mode="signature")

    strict_applier = SOPOneSiteEffective(sop, psi, psi.root)
    strict_applier.build_env_cache(cache_mode="term")
    strict_action = strict_applier.apply(cache_mode="term")

    assert len(strict_applier._env_cache) > len(signature_applier._env_cache)
    np.testing.assert_allclose(strict_action, signature_action, atol=1e-12)


def test_all_nodes_active_scope_records_all_active_tensors_and_matches_ttno():
    args = SimpleNamespace(timeout_sec=120, memory_limit_mb=0.0, max_phonon_basis=4, active_scope="all_nodes")
    _, _, psi = build_hubbard_junction_case(n_lead=1, n_phonon=0)

    rows = _run_point("lead_only", 1, 0, 0, args, "test")

    assert {row["method"] for row in rows} == {
        "ttno_with_env",
        "sop_no_env",
        "sop_mctdh_like_state_env",
        "sop_env_plus_operator_cache",
    }
    assert {row["quantity"] for row in rows} == {"local_effective_1site_apply_all_nodes"}
    assert {row["n_active_nodes"] for row in rows} == {len(psi.node_list)}
    for row in rows:
        assert row["status"] == "ok"
        assert row["relative_error_vs_ttno"] < 1e-12


def test_strict_mctdh_state_env_reuses_term_messages_across_active_nodes():
    args = SimpleNamespace(timeout_sec=120, memory_limit_mb=0.0, max_phonon_basis=4, active_scope="all_nodes")
    tree, terms, psi = build_hubbard_junction_case(n_lead=1, n_phonon=0)
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)

    rows = _run_point("lead_only", 1, 0, 0, args, "test")
    state_env_row = next(row for row in rows if row["method"] == "sop_mctdh_like_state_env")
    expected_directed_edge_messages = sop.n_terms * 2 * (len(psi.node_list) - 1)

    assert state_env_row["status"] == "ok"
    assert state_env_row["relative_error_vs_ttno"] < 1e-12
    assert state_env_row["n_env_cache_entries"] == expected_directed_edge_messages


def test_ren_variable_scaling_points_cover_site_bond_and_primitive_basis():
    args = SimpleNamespace(
        scaling_path="ren_variables",
        lead_values="4 8",
        balanced_pairs="4:1",
        state_bond_values="1 2",
        primitive_basis_values="2 4",
        state_bond_base_lead=4,
        state_bond_base_phonon=0,
        primitive_basis_base_lead=2,
        primitive_basis_base_phonon=2,
    )

    paths = dict(_scaling_points(args))

    assert [point[:2] for point in paths["lead_only"]] == [(4, 0), (8, 0)]
    assert paths["state_bond"] == [(4, 0, 1, None), (4, 0, 2, None)]
    assert paths["primitive_basis"] == [(2, 2, 1, 2), (2, 2, 1, 4)]


def test_primitive_basis_scaling_can_use_nontrivial_state_bond():
    args = SimpleNamespace(
        scaling_path="primitive_basis",
        primitive_basis_values="4 8",
        primitive_basis_base_lead=1,
        primitive_basis_base_phonon=8,
        primitive_basis_state_bond=16,
    )

    paths = dict(_scaling_points(args))

    assert paths["primitive_basis"] == [(1, 8, 16, 4), (1, 8, 16, 8)]


def test_build_hubbard_junction_case_can_force_primitive_basis_dimension():
    tree, _, _ = build_hubbard_junction_case(
        n_lead=1,
        n_phonon=2,
        force_phonon_basis=6,
    )

    sho_dims = [
        basis.nbas
        for basis in tree.basis_list
        if basis.__class__.__name__ == "BasisSHO"
    ]
    assert sho_dims == [6, 6]


def test_run_benchmark_checkpoints_completed_repeats(tmp_path, monkeypatch):
    calls = 0

    def fake_run_point(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        row = {field: math.nan for field in RAW_FIELDS}
        row.update({
            "case_name": "checkpoint_test",
            "scaling_path": "lead_only",
            "n_lead": 1,
            "n_phonon": 0,
            "n_total_sites": 6,
            "n_sop_terms": 12,
            "method": "ttno_with_env",
            "repeat_id": 0,
            "time_total_sec": 1.0,
            "status": "ok",
        })
        return [row]

    monkeypatch.setattr(benchmark_module, "_scaling_points", lambda args: [("lead_only", [(1, 0, 1, None)])])
    monkeypatch.setattr(benchmark_module, "_run_point", fake_run_point)
    monkeypatch.setattr(benchmark_module, "mark_overhead_rows", lambda rows: None)

    args = SimpleNamespace(
        repeats=2,
        output=tmp_path / "raw.csv",
        fit_output=tmp_path / "fits.csv",
        stop_after_consecutive_failures=2,
        max_extra_points=0,
        alpha_stability_tol=0.25,
    )

    with pytest.raises(KeyboardInterrupt):
        run_benchmark(args)

    with args.output.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["case_name"] == "checkpoint_test"
