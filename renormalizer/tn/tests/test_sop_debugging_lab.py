import json
from pathlib import Path

from benchmarks.sop_debugging_lab import (
    build_lab_case,
    compare_cache_modes,
    summarize_strict_cache,
    summarize_symbolic_terms,
    summarize_tree_local_ops,
    summarize_ttno,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
NOTEBOOK = REPO_ROOT / "notebooks" / "sop_debugging_lab.ipynb"


def _load_notebook():
    return json.loads(NOTEBOOK.read_text())


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
    assert cache_comparison["signature_entries"] < cache_comparison["term_entries"]
    assert cache_comparison["signature_metadata"] == {
        "method": "sop_env_plus_operator_cache",
        "purpose": "explanatory",
        "is_optimized": True,
        "is_strict": False,
    }
    assert ttno["max_bond"] == max(ctx["ttno"].bond_dims)


def test_notebook_contains_all_investigations_formulas_and_recap():
    notebook = _load_notebook()
    assert notebook["metadata"]["kernelspec"]["name"] == "reno-3.9"
    assert notebook["metadata"]["kernelspec"]["display_name"] == "Python (reno-3.9)"
    markdown = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown"
    )
    for number in range(1, 11):
        assert f"Investigation {number}" in markdown
    assert "# Investigation 1 — End-to-End Experiment Map" in markdown
    assert r"H = \sum_l c_l" in markdown
    assert r"E_{l,u\rightarrow v}" in markdown
    assert "What changed / Why / Effect" in markdown
    assert "local_effective_1site_apply_all_nodes" in markdown
    assert "signature_metadata" in markdown
    for section in (
        "Supervisor question",
        "Formula",
        "Runnable observation",
        "Exact breakpoint",
        "Inspect",
        "Answer prompt",
        "Expected observation",
        "Three-sentence oral explanation",
    ):
        assert markdown.count(section) >= 10


def test_notebook_code_cells_execute_from_notebooks_directory(monkeypatch, capsys):
    notebook = _load_notebook()
    monkeypatch.chdir(NOTEBOOK.parent)
    namespace = {"__name__": "__sop_lab_test__"}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), str(NOTEBOOK), "exec"), namespace)

    assert namespace["REPO_ROOT"] == REPO_ROOT
    assert namespace["RUN_BREAKPOINTS"] is False
    assert namespace["LAB_COMPLETE"] is True
    assert {row["status"] for row in namespace["rows"]} == {"ok"}

    no_env = namespace["no_env_observation"]
    assert no_env["n_terms_accumulated"] == 13
    assert no_env["single_term_tensor_elements"] > 0
    assert no_env["final_state_tensor_elements"] > no_env["single_term_tensor_elements"]
    assert no_env["final_max_bond"] > no_env["input_max_bond"]

    formal_trace = namespace["formal_trace"]
    assert formal_trace["manifest_records"] == 189
    assert formal_trace["repeat_ids"] == [0, 1, 2]
    assert formal_trace["selected_task_id"] == 3
    assert formal_trace["payload_identity_verified"] is True
    assert formal_trace["completed_snapshots"] == 189
    assert formal_trace["missing_task_ids"] == []
    assert formal_trace["summary_rows"] == 63
    assert formal_trace["fit_rows"] == 18
    assert formal_trace["plot_function"] == "benchmarks.plot_li2024_operator_scaling.plot"
    assert formal_trace["plot_output_bytes"] > 0

    output = capsys.readouterr().out
    assert "resolved op_mat: BasisSHO.op_mat" in output
    assert "op_mat return: renormalizer/model/basis.py:394" in output
    assert "outer term actions accumulated: 13" in output
    assert "payload identity verified: True" in output
    assert "completed snapshots: 189 / 189" in output
    assert "plot: benchmarks.plot_li2024_operator_scaling.plot" in output
