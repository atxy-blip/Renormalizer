import pytest

from renormalizer import BasisHalfSpin, Model, Mpo, Op
from renormalizer.mps.backend import np
from renormalizer.tn import BasisTree, SOPBaselineOperator, TTNO, TTNS


def _physical_order(tree):
    return [b for b in tree.basis_list if b.__class__.__name__ != "BasisDummy"]


def test_tiny_sop_and_ttno_match_dense_exact_operator():
    basis_list = [BasisHalfSpin(i) for i in range(3)]
    tree = BasisTree.binary(basis_list)
    terms = [
        Op("Z", 0, 0.3),
        Op("+ -", [0, 1], 0.7),
        Op("- +", [1, 2], -0.2),
        Op("+ - + -", [0, 0, 1, 1], 0.4),
        Op("X", 2, 0.1),
    ]

    dense_ref = Mpo(Model(basis_list, terms)).todense()
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)

    np.testing.assert_allclose(sop.to_dense_small_system(basis_list), dense_ref, atol=1e-14)
    np.testing.assert_allclose(ttno.todense(basis_list), dense_ref, atol=1e-14)

    psi = TTNS.random(tree, qntot=0, m_max=4).to_complex()
    psi_dense = psi.todense(basis_list).ravel()
    np.testing.assert_allclose(sop.apply_to_ttns(psi).todense(basis_list).ravel(), dense_ref @ psi_dense, atol=1e-12)
    np.testing.assert_allclose(ttno.apply(psi).todense(basis_list).ravel(), dense_ref @ psi_dense, atol=1e-12)


def test_sop_apply_does_not_construct_term_ttnos(monkeypatch):
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    tree = BasisTree.binary(basis_list)
    terms = [Op("X", 0, 0.5), Op("Z X", [0, 1], 0.2)]
    psi = TTNS(tree, condition={})
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)

    def fail_if_called(_term):
        raise AssertionError("apply_to_ttns must not construct per-term TTNO objects")

    monkeypatch.setattr(sop, "_term_ttno", fail_if_called)
    result = sop.apply_to_ttns(psi)
    ref = TTNO(tree, terms).apply(psi)
    np.testing.assert_allclose(result.todense(basis_list).ravel(), ref.todense(basis_list).ravel(), atol=1e-12)


def test_sop_apply_has_explicit_no_env_entrypoint():
    basis_list = [BasisHalfSpin(i) for i in range(3)]
    tree = BasisTree.binary(basis_list)
    terms = [Op("X", 0, 0.5), Op("Z X", [0, 2], 0.2)]
    psi = TTNS.random(tree, qntot=0, m_max=4).to_complex()
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)

    default = sop.apply_to_ttns(psi).todense(basis_list)
    explicit = sop.apply_to_ttns_no_env(psi).todense(basis_list)
    by_method = sop.apply_to_ttns(psi, method="sop_no_env").todense(basis_list)
    by_short_method = sop.apply_to_ttns(psi, method="no_env").todense(basis_list)

    np.testing.assert_allclose(explicit, default, atol=1e-12)
    np.testing.assert_allclose(by_method, default, atol=1e-12)
    np.testing.assert_allclose(by_short_method, default, atol=1e-12)


def test_sop_apply_rejects_with_env_until_implemented():
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    tree = BasisTree.binary(basis_list)
    psi = TTNS(tree, condition={})
    sop = SOPBaselineOperator.from_symbolic_terms([Op("X", 0, 0.5)], tree)

    with pytest.raises(NotImplementedError, match="sop_with_env"):
        sop.apply_to_ttns(psi, method="sop_with_env")


def test_identity_only_sop_scales_state_without_local_work():
    basis_list = [BasisHalfSpin(i) for i in range(3)]
    tree = BasisTree.binary(basis_list)
    psi = TTNS.random(tree, qntot=0, m_max=3).to_complex()
    sop = SOPBaselineOperator.from_symbolic_terms([Op.identity(0, factor=2.5)], tree)

    result = sop.apply_to_ttns(psi)
    np.testing.assert_allclose(result.todense(basis_list), 2.5 * psi.todense(basis_list), atol=1e-12)
    assert sop.count_nontrivial_local_ops() == 0


def test_term_order_does_not_change_sop_result():
    basis_list = [BasisHalfSpin(i) for i in range(3)]
    tree = BasisTree.binary(basis_list)
    terms = [Op("X", 0, 0.1), Op("Z X", [0, 2], 0.2), Op("+ -", [1, 2], -0.3)]
    psi = TTNS.random(tree, qntot=0, m_max=4).to_complex()

    dense1 = SOPBaselineOperator.from_symbolic_terms(terms, tree).apply_to_ttns(psi).todense(basis_list)
    dense2 = SOPBaselineOperator.from_symbolic_terms(list(reversed(terms)), tree).apply_to_ttns(psi).todense(basis_list)
    np.testing.assert_allclose(dense1, dense2, atol=1e-12)


def test_repeated_terms_are_flattened_repeated_traversals():
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    tree = BasisTree.binary(basis_list)
    base = Op("X X", [0, 1], 0.25)
    psi = TTNS(tree, condition={})

    once = SOPBaselineOperator.from_symbolic_terms([base], tree).apply_to_ttns(psi).todense(basis_list)
    repeated = SOPBaselineOperator.from_symbolic_terms([base] * 5, tree)
    repeated_dense = repeated.apply_to_ttns(psi).todense(basis_list)

    assert repeated.n_terms == 5
    np.testing.assert_allclose(repeated_dense, 5 * once, atol=1e-12)


def test_non_hermitian_current_like_operator_matches_ttno():
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    tree = BasisTree.binary(basis_list)
    current_terms = [Op("+ -", [0, 1], 1.0), Op("- +", [0, 1], -1.0)]
    psi = TTNS.random(tree, qntot=0, m_max=3).to_complex()

    sop = SOPBaselineOperator.from_symbolic_terms(current_terms, tree)
    ttno = TTNO(tree, current_terms)
    np.testing.assert_allclose(
        sop.apply_to_ttns(psi).todense(_physical_order(tree)).ravel(),
        ttno.apply(psi).todense(_physical_order(tree)).ravel(),
        atol=1e-12,
    )
    np.testing.assert_allclose(sop.expectation(psi), psi.expectation(ttno), atol=1e-12)
