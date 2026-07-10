from types import SimpleNamespace

from benchmarks.benchmark_adaptive_operator_env import (
    SOPOneSiteEffective,
    _run_point,
    build_hubbard_junction_case,
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
