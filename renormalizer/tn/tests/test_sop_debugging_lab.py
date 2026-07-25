from benchmarks.sop_debugging_lab import (
    build_lab_case,
    compare_cache_modes,
    summarize_strict_cache,
    summarize_symbolic_terms,
    summarize_tree_local_ops,
    summarize_ttno,
)


def test_lab_case_exposes_real_small_li2024_objects():
    ctx = build_lab_case()

    assert len(ctx["terms"]) == 13
    assert ctx["sop"].n_terms == 13
    assert max(ctx["psi"].bond_dims) == 2
    assert ctx["metadata"]["quantity"] == "local_effective_1site_apply_all_nodes"


def test_lab_summaries_make_term_and_cache_structure_observable():
    ctx = build_lab_case()
    terms = summarize_symbolic_terms(ctx["terms"], ctx["sop"])
    local = summarize_tree_local_ops(ctx["tree"], ctx["sop"].terms[-1])
    ctx["strict_env"].build_env_cache()
    strict = summarize_strict_cache(ctx["strict_env"])
    cache_comparison = compare_cache_modes(ctx["sop"], ctx["psi"])
    ttno = summarize_ttno(ctx["ttno"])

    assert terms[0]["symbol"] == "sigma_x"
    assert any(row["is_nontrivial"] for row in local)
    assert strict["key_shape"] == "(source_node_idx, target_node_idx, term_index)"
    assert strict["n_entries"] == 2 * (len(ctx["tree"].node_list) - 1) * ctx["sop"].n_terms
    assert cache_comparison["signature_entries"] <= cache_comparison["term_entries"]
    assert ttno["max_bond"] == max(ctx["ttno"].bond_dims)
