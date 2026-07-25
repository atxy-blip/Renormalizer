"""Stable, notebook-friendly inspection helpers for the SOP debugging lab."""

from benchmarks.benchmark_adaptive_operator_env import (
    SOP_CACHE_SIGNATURE,
    SOP_CACHE_TERM,
    SOPMCTDHSweepEnvironment,
    SOPOneSiteEffective,
)
from benchmarks.benchmark_li2024_operator_env import build_li2024_spin_boson_case
from renormalizer.tn import SOPBaselineOperator, TTNO


def _builtin(value):
    """Convert backend values recursively to built-in notebook display values."""

    if isinstance(value, tuple):
        return tuple(_builtin(item) for item in value)
    if isinstance(value, list):
        return [_builtin(item) for item in value]
    if isinstance(value, dict):
        return {_builtin(key): _builtin(item) for key, item in value.items()}
    return value.item() if hasattr(value, "item") else value


def build_lab_case():
    """Build the fixed, small Li.W.2024 case used throughout the lab."""

    tree, terms, psi = build_li2024_spin_boson_case(
        n_modes=4,
        state_bond=2,
        primitive_basis=3,
        contract_primitive=True,
    )
    sop = SOPBaselineOperator.from_symbolic_terms(terms, tree)
    ttno = TTNO(tree, terms)
    strict_env = SOPMCTDHSweepEnvironment(sop, psi)
    return {
        "tree": tree,
        "terms": terms,
        "psi": psi,
        "sop": sop,
        "ttno": ttno,
        "strict_env": strict_env,
        "active_nodes": list(psi.node_list),
        "metadata": {
            "case_name": "li2024_spin_boson",
            "n_modes": 4,
            "state_bond": 2,
            "primitive_basis": 3,
            "contract_primitive": True,
            "quantity": "local_effective_1site_apply_all_nodes",
        },
    }


def summarize_symbolic_terms(terms, sop):
    """Expose the symbolic and flattened-SOP view of every Hamiltonian term."""

    return [
        {
            "term_index": term_index,
            "symbol": str(term.symbol),
            "dofs": [str(dof) for dof in term.dofs],
            "factor": _builtin(term.factor),
            "sop_coefficient": _builtin(sop_term.coeff),
            "n_nontrivial_local_ops": sop_term.n_nontrivial_local_ops,
            "local_op_node_idxs": sorted(sop_term.local_ops),
        }
        for term_index, (term, sop_term) in enumerate(zip(terms, sop.terms))
    ]


def summarize_tree_local_ops(tree, sop_term):
    """Show which local factor a single SOP product term has at each tree node."""

    rows = []
    for node_index, node in enumerate(tree.node_list):
        local_op = sop_term.local_ops.get(node_index)
        rows.append({
            "node_index": node_index,
            "dofs": [str(basis.dof) for basis in node.basis_sets],
            "physical_bond_dims": tuple(int(dim) for dim in node.pbond_dims),
            "is_nontrivial": local_op is not None,
            "symbol": None if local_op is None else str(local_op.symbol),
            "operator": None if local_op is None else _builtin(local_op.to_tuple()),
        })
    return rows


def summarize_strict_cache(environment):
    """Summarize the strict whole-sweep SOP environment cache."""

    keys = sorted(environment._env_cache)
    return {
        "key_shape": "(source_node_idx, target_node_idx, term_index)",
        "n_entries": len(keys),
        "representative_keys": _builtin(keys[:3]),
        "n_terms": environment.sop.n_terms,
    }


def compare_cache_modes(sop, psi, active_node=None):
    """Compare a strict term cache with an explanatory optimized signature cache.

    The signature cache is the non-strict ``sop_env_plus_operator_cache``
    optimization. It is included for explanation only, not as a formal method.
    """

    active_node = active_node or psi.root
    term_cache = SOPOneSiteEffective(sop, psi, active_node)
    signature_cache = SOPOneSiteEffective(sop, psi, active_node)
    term_cache.build_env_cache(SOP_CACHE_TERM)
    signature_cache.build_env_cache(SOP_CACHE_SIGNATURE)
    term_keys = sorted(term_cache._env_cache)
    signature_keys = sorted(signature_cache._env_cache)
    return {
        "active_node_idx": psi.node_idx[active_node],
        "term_entries": len(term_keys),
        "signature_entries": len(signature_keys),
        "term_representative_keys": _builtin(term_keys[:3]),
        "signature_representative_keys": _builtin(signature_keys[:3]),
        "signature_metadata": {
            "method": "sop_env_plus_operator_cache",
            "purpose": "explanatory",
            "is_optimized": True,
            "is_strict": False,
        },
    }


def summarize_ttno(ttno):
    """Return the compressed TTNO topology in a print-friendly form."""

    bond_dims = [int(dim) for dim in ttno.bond_dims]
    return {
        "n_nodes": len(ttno.node_list),
        "bond_dims": bond_dims,
        "max_bond": max(bond_dims),
    }
