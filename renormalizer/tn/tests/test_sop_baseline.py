import pytest

from renormalizer import BasisHalfSpin, Model, Mpo, Op
from renormalizer.mps.backend import np
from renormalizer.model.model import heisenberg_ops
from renormalizer.tn import BasisTree, SOPBaselineOperator, TTNO, TTNS
from renormalizer.tn.node import TreeNodeBasis


def _multi_site_tree(basis_list):
    root = TreeNodeBasis([basis_list[0], basis_list[1]])
    child = TreeNodeBasis([basis_list[2]])
    root.add_child(child)
    return BasisTree(root)


@pytest.mark.parametrize("basis_tree_factory", [BasisTree.binary, _multi_site_tree])
def test_sop_baseline_matches_ttno_dense_apply_and_expectation(basis_tree_factory):
    basis_list = [BasisHalfSpin(i) for i in range(3)]
    basis_tree = basis_tree_factory(basis_list)
    terms = heisenberg_ops(3) + [Op("X Z", [0, 2], 0.17)]
    psi = TTNS.random(basis_tree, qntot=0, m_max=4)

    sop = SOPBaselineOperator.from_symbolic_terms(terms, basis_tree)
    ttno = TTNO(basis_tree, terms)

    assert sop.n_terms == len(terms)
    assert sop.count_nontrivial_local_ops() >= len(terms)
    assert sop.estimate_storage() > 0
    np.testing.assert_allclose(sop.to_dense_small_system(), ttno.todense(), atol=1e-14)
    np.testing.assert_allclose(
        sop.apply_to_ttns(psi).todense().ravel(),
        ttno.apply(psi).todense().ravel(),
        atol=1e-12,
    )
    np.testing.assert_allclose(sop.expectation(psi), psi.expectation(ttno), atol=1e-12)


def test_sop_baseline_accepts_model_and_non_hermitian_complex_terms():
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    basis_tree = BasisTree.binary(basis_list)
    terms = [Op("+ -", [0, 1], 1.2 + 0.4j), Op("Z", 0, -0.3j)]
    model = Model(basis_list, terms)
    psi = TTNS.random(basis_tree, qntot=0, m_max=3).to_complex()

    sop = SOPBaselineOperator.from_symbolic_terms(model, basis_tree)
    ttno = TTNO(basis_tree, model.ham_terms)

    assert sop.terms[0].coeff == pytest.approx(1.2 + 0.4j)
    np.testing.assert_allclose(sop.to_dense_small_system(), ttno.todense(), atol=1e-14)
    np.testing.assert_allclose(
        sop.apply_to_ttns(psi).todense().ravel(),
        ttno.apply(psi).todense().ravel(),
        atol=1e-12,
    )
    np.testing.assert_allclose(sop.expectation(psi), psi.expectation(ttno), atol=1e-12)


def test_sop_baseline_uses_same_symbolic_convention_as_mpo():
    basis_list = [BasisHalfSpin(i) for i in range(2)]
    terms = [Op("X", 0, 0.5), Op("Y X", [0, 1], 0.2j)]
    basis_tree = BasisTree.binary(basis_list)

    sop_dense = SOPBaselineOperator.from_symbolic_terms(terms, basis_tree).to_dense_small_system(basis_list)
    mpo_dense = Mpo(Model(basis_list, terms)).todense()

    np.testing.assert_allclose(sop_dense, mpo_dense, atol=1e-14)
