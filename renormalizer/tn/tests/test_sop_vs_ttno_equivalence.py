from benchmarks.benchmark_sop_vs_ttno import build_hubbard_junction_case
from renormalizer.mps.backend import np
from renormalizer.tn import SOPBaselineOperator, TTNO


def _assert_apply_and_expectation_match(tree, terms, psi, atol=1e-10):
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    order = [b for b in tree.basis_list if b.__class__.__name__ != "BasisDummy"]

    sop_psi = sop.apply_to_ttns(psi).todense(order).ravel()
    ttno_psi = ttno.apply(psi).todense(order).ravel()
    denom = np.linalg.norm(ttno_psi)
    rel = np.linalg.norm(sop_psi - ttno_psi) / denom if denom != 0 else np.linalg.norm(sop_psi - ttno_psi)

    assert rel < atol
    np.testing.assert_allclose(sop.expectation(psi), psi.expectation(ttno), atol=atol)


def test_sop_matches_ttno_for_hubbard_junction_hamiltonian_and_current():
    # This uses the same symbolic construction pattern as
    # ../ttns-test/junction_zt_hubbard.py at a reduced benchmark size.
    tree, ham_terms, current_terms, psi = build_hubbard_junction_case(n_lead=2, n_phonon=1)

    _assert_apply_and_expectation_match(tree, ham_terms, psi)
    _assert_apply_and_expectation_match(tree, current_terms, psi)


def test_sop_matches_ttno_for_hubbard_junction_phonon_scaling_point():
    tree, ham_terms, current_terms, psi = build_hubbard_junction_case(n_lead=1, n_phonon=2)

    _assert_apply_and_expectation_match(tree, ham_terms, psi)
    _assert_apply_and_expectation_match(tree, current_terms, psi)
