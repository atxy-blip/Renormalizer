import numpy as np

from benchmarks.nature_plot_style import METHOD_STYLES
from benchmarks.plot_operator_env_scaling import (
    PUBLICATION_METHODS,
    LEGEND_KWARGS,
    METHOD_COLORS,
    REFERENCE_ALPHA,
    SCALING_PANELS,
    compute_fits,
    plot_publication_time,
    reference_annotation,
    reference_curve,
    reference_curve_last_half,
    method_legend_label,
    summarize,
)


def test_publication_methods_exclude_operator_cache():
    assert PUBLICATION_METHODS == (
        "sop_no_env",
        "sop_mctdh_like_state_env",
        "ttno_with_env",
    )
    assert "sop_env_plus_operator_cache" not in PUBLICATION_METHODS


def test_publication_method_colors_match_shared_nature_palette():
    assert METHOD_COLORS == {
        method: METHOD_STYLES[method]["color"]
        for method in PUBLICATION_METHODS
    }


def test_reference_curves_have_requested_log_log_slopes():
    x = np.array([16.0, 32.0, 64.0])
    y = np.array([2.0, 8.0, 32.0])

    for alpha in REFERENCE_ALPHA.values():
        x_ref, y_ref = reference_curve(x, y, alpha)
        measured = np.diff(np.log(y_ref)) / np.diff(np.log(x_ref))
        np.testing.assert_allclose(measured, alpha)


def test_last_half_reference_ends_on_last_data_point():
    x = np.array([10.0, 20.0, 30.0, 50.0, 70.0, 100.0])
    y = np.array([1.0, 1.5, 2.0, 4.0, 8.0, 16.0])

    x_ref, y_ref = reference_curve_last_half(x, y, 4.0)

    np.testing.assert_array_equal(x_ref, x[len(x) // 2 :])
    assert x_ref[-1] == x[-1]
    assert y_ref[-1] == y[-1]
    measured = np.diff(np.log(y_ref)) / np.diff(np.log(x_ref))
    np.testing.assert_allclose(measured, 4.0)


def test_legend_label_does_not_include_fitted_alpha():
    assert method_legend_label("ttno_with_env") == "TTNO with env"


def test_scaling_panels_match_ren_variables():
    assert [(panel.name, panel.x_axis, panel.symbol) for panel in SCALING_PANELS] == [
        ("site_number", "n_total_sites", "N"),
        ("state_bond", "state_max_bond", "M_s"),
        ("primitive_basis", "primitive_basis_dim", "d"),
    ]


def test_panels_have_fixed_theoretical_reference_slopes():
    site_panel, state_bond_panel, primitive_basis_panel = SCALING_PANELS

    assert dict(site_panel.reference_alpha_by_method) == REFERENCE_ALPHA
    assert dict(state_bond_panel.reference_alpha_by_method) == {
        method: 3.0 for method in PUBLICATION_METHODS
    }
    assert dict(primitive_basis_panel.reference_alpha_by_method) == {
        "sop_no_env": 0.0,
        "sop_mctdh_like_state_env": 0.0,
        "ttno_with_env": 4.0,
    }


def test_legend_is_positioned_inside_first_panel():
    assert LEGEND_KWARGS["loc"] == "upper left"
    assert LEGEND_KWARGS["frameon"] is False
    assert "fontsize" not in LEGEND_KWARGS
    assert "bbox_to_anchor" not in LEGEND_KWARGS


def test_reference_annotation_is_inline_proportional_label():
    assert reference_annotation("N", 3.0) == r"$\propto N^3$"
    assert reference_annotation("M_s", 2.0) == r"$\propto M_s^2$"
    assert reference_annotation("d", 1.0) == r"$\propto d^1$"
    assert reference_annotation("d", 0.0) == r"$\propto \mathrm{const}$"


def _raw_row(
    method,
    scaling_path,
    state_max_bond=1,
    primitive_basis=2,
    elapsed=1.0,
    n_total_sites=20,
    n_lead=4,
):
    return {
        "status": "ok",
        "method": method,
        "scaling_path": scaling_path,
        "n_lead": str(n_lead),
        "n_phonon": "2",
        "n_total_sites": str(n_total_sites),
        "n_sop_terms": "56",
        "n_active_nodes": "29",
        "tree_depth": "6",
        "n_sop_terms_times_n_total_sites": "1120",
        "n_sop_terms_times_n_active_nodes": "1624",
        "n_sop_terms_times_tree_depth": "336",
        "ttno_max_bond": "4",
        "ttno_mean_bond": "2.0",
        "state_max_bond": str(state_max_bond),
        "local_basis_summary": f'{{"BasisSHO:{primitive_basis}": 2}}',
        "time_total_sec": str(elapsed),
        "time_env_build_sec": "0.1",
        "time_term_loop_sec": "0.0",
        "time_apply_sec": str(elapsed - 0.1),
        "n_env_cache_entries": "0",
        "relative_error_vs_ttno": "0.0",
    }


def test_summarize_keeps_state_bond_and_primitive_basis_points_distinct():
    rows = []
    for method in PUBLICATION_METHODS:
        rows.extend([
            _raw_row(method, "state_bond", state_max_bond=2, elapsed=2.0),
            _raw_row(method, "state_bond", state_max_bond=4, elapsed=4.0),
            _raw_row(method, "primitive_basis", primitive_basis=4, elapsed=4.0),
            _raw_row(method, "primitive_basis", primitive_basis=8, elapsed=8.0),
        ])

    summary = summarize(rows)
    state_points = [row for row in summary if row["scaling_path"] == "state_bond"]
    basis_points = [row for row in summary if row["scaling_path"] == "primitive_basis"]

    assert sorted({row["state_max_bond"] for row in state_points}) == [2, 4]
    assert sorted({row["primitive_basis_dim"] for row in basis_points}) == [4, 8]
    assert len(state_points) == 2 * len(PUBLICATION_METHODS)
    assert len(basis_points) == 2 * len(PUBLICATION_METHODS)


def test_publication_plot_writes_paired_formal_outputs(tmp_path):
    rows = []
    for method in PUBLICATION_METHODS:
        rows.extend([
            _raw_row(
                method,
                "site_number",
                n_total_sites=20,
                n_lead=4,
                elapsed=2.0,
            ),
            _raw_row(
                method,
                "site_number",
                n_total_sites=36,
                n_lead=8,
                elapsed=4.0,
            ),
            _raw_row(method, "state_bond", state_max_bond=2, elapsed=2.0),
            _raw_row(method, "state_bond", state_max_bond=4, elapsed=4.0),
            _raw_row(method, "primitive_basis", primitive_basis=4, elapsed=4.0),
            _raw_row(method, "primitive_basis", primitive_basis=8, elapsed=8.0),
        ])

    summary = summarize(rows)
    fits = compute_fits(summary)
    pdf, png = plot_publication_time(summary, fits, tmp_path / "ren")

    assert pdf.name == "ren_scaling_three_panel.pdf"
    assert png.name == "ren_scaling_three_panel.png"
    assert pdf.stat().st_size > 0
    assert png.stat().st_size > 0
