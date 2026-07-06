"""ML-MCTDH-style sum-of-products operator baseline for TTNS comparisons.

This module is intentionally a baseline implementation for methodology
benchmarks.  It keeps a symbolic Hamiltonian as a flat sum of product terms and
applies those terms one by one on the same TTNS/tree/basis used by the TTNO
path.  It is not a production TTNO construction path and it is not an
implementation of Heidelberg ML-MCTDH propagation or SPF equations.
"""

from dataclasses import dataclass
from functools import reduce
from operator import mul
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union

from renormalizer import Model, Op
from renormalizer.model.op import OpSum
from renormalizer.mps.backend import np
from renormalizer.tn.treebase import BasisTree


@dataclass(frozen=True)
class SOPTerm:
    """Single flattened SOP product term.

    Parameters
    ----------
    coeff
        Scalar coefficient multiplying the product operator.
    local_ops
        Mapping from ``BasisTree`` node index to the already grouped local
        symbolic operator on that node.  Missing nodes are identities and are
        skipped during application.  Existing fermionic parity/Jordan-Wigner
        strings are preserved exactly as symbols in these local operators.
    """

    coeff: Union[float, complex]
    local_ops: Mapping[int, Op]

    @classmethod
    def from_op(cls, op: Op, basis: BasisTree) -> "SOPTerm":
        """Convert an existing symbolic ``Op`` term into one SOP product term."""

        local_ops, coeff = _split_op_by_tree_node(op, basis)
        return cls(coeff=coeff, local_ops=local_ops)

    def to_op(self, basis: BasisTree) -> Op:
        """Reconstruct this SOP product term as a single symbolic ``Op``."""

        if not self.local_ops:
            return basis.identity_op * self.coeff
        ordered_ops = [self.local_ops[idx] for idx in sorted(self.local_ops)]
        op = Op.product(ordered_ops)
        return op * self.coeff

    @property
    def n_nontrivial_local_ops(self) -> int:
        """Number of non-identity local factors in this product term."""

        return len(self.local_ops)


class SOPBaselineOperator:
    """Flat SOP operator baseline applied term by term on a TTNS.

    The class models the operator-representation layer of traditional
    ML-MCTDH-style sum-of-products calculations: a Hamiltonian is represented as
    ``sum_r c_r prod_k h_r^(k)`` and each product term is applied separately.
    It deliberately does not compress the full term list into a TTNO/MPO.
    """

    def __init__(self, terms: Iterable[Union[SOPTerm, Op]], basis: BasisTree):
        self.basis = basis
        self.terms: List[SOPTerm] = []
        for term in terms:
            sop_term = term if isinstance(term, SOPTerm) else SOPTerm.from_op(term, basis)
            if sop_term.coeff == 0:
                continue
            self.terms.append(sop_term)
        self._term_ttno_cache = {}
        self._local_factor_cache = {}

    @classmethod
    def from_symbolic_terms(
        cls,
        model_or_terms: Union[Model, Iterable[Op], Op, OpSum],
        tree: BasisTree,
        basis=None,
    ) -> "SOPBaselineOperator":
        """Build the flat SOP baseline from existing symbolic model terms.

        ``basis`` is accepted for API symmetry with TTNO builders but the local
        basis is already contained in ``tree``.
        """

        del basis
        if isinstance(model_or_terms, Model):
            terms = model_or_terms.ham_terms
        elif isinstance(model_or_terms, Op):
            terms = [model_or_terms]
        elif isinstance(model_or_terms, OpSum):
            terms = list(model_or_terms)
        else:
            terms = list(model_or_terms)
        return cls(terms, tree)

    @property
    def n_terms(self) -> int:
        """Number of flattened SOP product terms."""

        return len(self.terms)

    def count_nontrivial_local_ops(self) -> int:
        """Count all explicit non-identity local factors across SOP terms."""

        return sum(term.n_nontrivial_local_ops for term in self.terms)

    def estimate_storage(self) -> int:
        """Estimate dense local-matrix storage for this flat SOP list.

        The estimate counts the scalar coefficient and all explicitly stored
        local matrices term by term.  Identity sites are skipped.  No sharing
        across terms is assumed, matching the flattened SOP baseline.
        """

        total = self.n_terms
        for term in self.terms:
            for node_idx in term.local_ops:
                dims = self.basis.node_list[node_idx].pbond_dims
                local_dim = int(reduce(mul, dims, 1))
                total += local_dim * local_dim
        return int(total)

    def apply_to_ttns(self, psi):
        """Apply the SOP operator to ``psi`` by summing independent term actions."""

        result = None
        for term in self.terms:
            term_psi = self._apply_term_to_ttns(term, psi)
            if result is None:
                result = term_psi
            else:
                result = result.add(term_psi)
        if result is None:
            return psi.scale(0)
        return result

    def expectation(self, psi):
        """Compute ``<psi|O|psi>`` without constructing a compressed TTNO."""

        return self.apply_to_ttns(psi).overlap(psi)

    def to_dense_small_system(self, order: Optional[List] = None):
        """Convert the flat SOP operator to a dense matrix for tiny tests only."""

        if self.n_terms == 0:
            dim = int(np.prod([b.nbas for b in (order or self.basis.basis_list)]))
            return np.zeros((dim, dim))
        dense = None
        for term in self.terms:
            term_dense = self._term_ttno(term).todense(order)
            dense = term_dense if dense is None else dense + term_dense
        return dense

    def _term_ttno(self, term: SOPTerm):
        """Construct/cache one product-term TTNO without full SOP compression."""

        # Import lazily to avoid a module import cycle with renormalizer.tn.tree.
        from renormalizer.tn.tree import TTNO

        key = (term.coeff, tuple(sorted((idx, op.to_tuple()) for idx, op in term.local_ops.items())))
        if key not in self._term_ttno_cache:
            self._term_ttno_cache[key] = TTNO(self.basis, [term.to_op(self.basis)])
        return self._term_ttno_cache[key]

    def _apply_term_to_ttns(self, term: SOPTerm, psi):
        """Apply one product term by local physical-axis matrix products."""

        if not term.local_ops:
            return psi.scale(term.coeff)

        new = psi.metacopy()
        subtree_qn = self._term_subtree_qn(term)
        for node_idx, (source_node, target_node) in enumerate(zip(psi, new)):
            tensor = source_node.tensor
            factors = self._local_matrix_factors(node_idx, term.local_ops.get(node_idx))
            physical_axis0 = len(source_node.children)
            for ibasis, mat in enumerate(factors):
                if mat is None:
                    continue
                tensor = _apply_matrix_on_axis(tensor, mat, physical_axis0 + ibasis)
            if source_node is psi.root:
                tensor = tensor * term.coeff
            target_node.tensor = tensor
            target_node.qn = source_node.qn + subtree_qn[node_idx]
        new.check_shape()
        return new

    def _term_subtree_qn(self, term: SOPTerm) -> Dict[int, np.ndarray]:
        qn_zero = np.zeros(self.basis.qn_size, dtype=int)
        subtree_qn = {}
        for basis_node in self.basis.postorder_list():
            node_idx = self.basis.node_idx[basis_node]
            op = term.local_ops.get(node_idx)
            qn = qn_zero.copy() if op is None else op.qn.copy()
            for child in basis_node.children:
                qn = qn + subtree_qn[self.basis.node_idx[child]]
            subtree_qn[node_idx] = qn
        return subtree_qn

    def _local_matrix_factors(self, node_idx: int, op: Optional[Op]) -> List[Optional[np.ndarray]]:
        basis_node = self.basis.node_list[node_idx]
        if op is None:
            return [None] * basis_node.n_sets

        key = (node_idx, op.to_tuple())
        if key in self._local_factor_cache:
            return self._local_factor_cache[key]

        local_model = Model(basis_node.basis_sets, [])
        elementary_ops, factor = op.split_elementary(local_model.dof_to_siteidx)
        elem_by_site = {}
        for elementary_op in elementary_ops:
            site_indices = {local_model.dof_to_siteidx[dof] for dof in elementary_op.dofs}
            assert len(site_indices) == 1
            elem_by_site[site_indices.pop()] = elementary_op

        factors: List[Optional[np.ndarray]] = []
        factor_applied = False
        for ibasis, basis_set in enumerate(basis_node.basis_sets):
            elementary_op = elem_by_site.get(ibasis)
            if elementary_op is None or elementary_op.is_identity:
                factors.append(None)
                continue
            mat = basis_set.op_mat(elementary_op)
            if not factor_applied:
                mat = mat * factor
                factor_applied = True
            factors.append(mat)
        if not factor_applied and factor != 1:
            for ibasis, basis_set in enumerate(basis_node.basis_sets):
                factors[ibasis] = np.eye(basis_set.nbas) * factor
                break
        self._local_factor_cache[key] = factors
        return factors


def _split_op_by_tree_node(op: Op, basis: BasisTree) -> Tuple[Dict[int, Op], Union[float, complex]]:
    """Split one symbolic ``Op`` into local factors grouped by BasisTree node."""

    model = Model(basis.basis_list, [])
    elementary_ops, coeff = op.split_elementary(model.dof_to_siteidx)
    local_ops: Dict[int, Op] = {}
    for elementary_op in elementary_ops:
        node_indices = {basis.dof2idx[dof] for dof in elementary_op.dofs}
        if len(node_indices) != 1:
            raise ValueError(f"Operator {elementary_op} spans multiple BasisTree nodes after splitting.")
        if elementary_op.is_identity:
            continue
        node_idx = node_indices.pop()
        if node_idx in local_ops:
            local_ops[node_idx] = local_ops[node_idx] * elementary_op
        else:
            local_ops[node_idx] = elementary_op
    return local_ops, coeff


def _apply_matrix_on_axis(tensor: np.ndarray, mat: np.ndarray, axis: int) -> np.ndarray:
    """Apply a local operator matrix to one physical axis of a TTNS tensor."""

    res = np.tensordot(mat, tensor, axes=(1, axis))
    return np.moveaxis(res, 0, axis)
