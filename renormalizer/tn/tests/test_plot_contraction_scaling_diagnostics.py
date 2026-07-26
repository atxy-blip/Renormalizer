import csv
from pathlib import Path

import pytest
import renormalizer
import benchmarks.plot_contraction_scaling_diagnostics as diagnostics

from benchmarks.plot_contraction_scaling_diagnostics import (
    COLORS,
    generate_figures,
    log_fit,
    read_summary,
    select_series,
)


def test_diagnostic_palette_uses_nature_semantics():
    assert COLORS["sop"] == "#00529B"
    assert COLORS["ttno"] == "#007A33"
    assert COLORS["paired"] == "#CC0000"


def test_summary_dimensions_are_parsed_and_series_are_sorted_numerically(tmp_path):
    path = tmp_path / "summary.csv"
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=(
            "panel", "kernel", "state_bond", "primitive_basis",
            "operator_bond", "contract_primitive", "n_repeats",
            "apply_sec_median", "apply_sec_std",
        ))
        writer.writeheader()
        for value in (10, 100, 20):
            writer.writerow({
                "panel": "internal_ms",
                "kernel": "sop_internal",
                "state_bond": value,
                "primitive_basis": 1,
                "operator_bond": 4,
                "contract_primitive": False,
                "n_repeats": 3,
                "apply_sec_median": value ** 4,
                "apply_sec_std": 0,
            })

    rows = read_summary(path)
    series = select_series(rows, "internal_ms", "sop_internal", "state_bond")

    assert [row["state_bond"] for row in series] == [10, 20, 100]
    assert all(isinstance(row["apply_sec_median"], float) for row in series)
    assert all(row["contract_primitive"] is False for row in series)


def test_log_fit_recovers_power_and_uses_requested_tail():
    rows = [
        {"x": float(x), "y": float(3 * x ** 4)}
        for x in (1, 2, 4, 8, 16, 32)
    ]

    fit = log_fit(rows, "x", "y", tail=4)

    assert fit["alpha"] == pytest.approx(4.0)
    assert fit["r2"] == pytest.approx(1.0)
    assert fit["n_points"] == 4
    assert fit["x_min"] == 4
    assert fit["x_max"] == 32


def _synthetic_summary_rows():
    rows = []
    for kernel, coefficient in (("sop_internal", 6), ("ttno_internal", 48)):
        for value in (10, 20, 40, 80):
            rows.append({
                "panel": "internal_ms", "kernel": kernel,
                "state_bond": value, "primitive_basis": 1,
                "operator_bond": 4, "contract_primitive": False,
                "n_repeats": 3,
                "optimized_flops_median": coefficient * value ** 4,
                "optimized_flops_std": 0,
                "apply_sec_median": coefficient * value ** 3.5 * 1e-9,
                "apply_sec_std": coefficient * value ** 3.5 * 1e-11,
            })
    for kernel, power, contracted in (
        ("ttno_leaf_paired", 4, False),
        ("ttno_leaf_contracted", 2, True),
    ):
        for value in (10, 20, 40, 80):
            rows.append({
                "panel": "leaf_d", "kernel": kernel,
                "state_bond": 20, "primitive_basis": value,
                "operator_bond": 4, "contract_primitive": contracted,
                "n_repeats": 3,
                "optimized_flops_median": 10 * value ** power,
                "optimized_flops_std": 0,
                "apply_sec_median": value ** (power - 0.3) * 1e-8,
                "apply_sec_std": value ** (power - 0.3) * 1e-10,
            })
    for kernel, power, contracted in (
        ("ttno_model_paired", 4, False),
        ("ttno_model_contracted", 2, True),
    ):
        for value in (10, 20, 40, 80):
            base = value ** power * 1e-7
            rows.append({
                "panel": "model_d", "kernel": kernel,
                "state_bond": 20, "primitive_basis": value,
                "operator_bond": 4, "contract_primitive": contracted,
                "n_repeats": 3,
                "operator_build_sec_median": 0.5 * base,
                "operator_build_sec_std": 0.01 * base,
                "environment_build_sec_median": 0.3 * base,
                "environment_build_sec_std": 0.01 * base,
                "expression_build_sec_median": 0.01,
                "expression_build_sec_std": 0.001,
                "apply_sec_median": 0.2 * base,
                "apply_sec_std": 0.01 * base,
                "time_total_sec_median": base + 0.01,
                "time_total_sec_std": 0.02 * base,
                "state_tensor_elements_median": 1000 + value ** (2 if not contracted else 1),
                "state_tensor_elements_std": 0,
                "operator_tensor_elements_median": 1000 + value ** power,
                "operator_tensor_elements_std": 0,
                "peak_memory_mb_median": 100 + value ** power * 1e-3,
                "peak_memory_mb_std": 1,
            })
    return rows


def test_process_memory_legend_has_a_clear_left_axis_inset(monkeypatch, tmp_path):
    captured_figures = []

    def capture_figure(fig, pdf_path):
        fig.canvas.draw()
        captured_figures.append(fig)
        return Path(pdf_path), Path(pdf_path).with_suffix(".png")

    monkeypatch.setattr(diagnostics, "save_pdf_png", capture_figure)
    diagnostics._plot_model_mechanism(_synthetic_summary_rows(), [], tmp_path)

    figure = captured_figures[0]
    axis = figure.axes[3]
    renderer = figure.canvas.get_renderer()
    legend_left = axis.get_legend().get_window_extent(renderer).x0
    axis_bounds = axis.get_window_extent(renderer)

    assert legend_left >= axis_bounds.x0 + 0.03 * axis_bounds.width


def test_generate_figures_writes_declared_artifacts(tmp_path):
    summary = tmp_path / "summary.csv"
    rows = _synthetic_summary_rows()
    fields = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with summary.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    outputs = generate_figures(summary, tmp_path / "figures")

    assert {path.name for path in outputs} == {
        "complexity_validation.pdf",
        "complexity_validation.png",
        "model_mechanism.pdf",
        "model_mechanism.png",
        "plot_fits.csv",
    }
    assert all(path.is_file() and path.stat().st_size > 0 for path in outputs)
    assert Path(outputs[-1]).read_text().count("largest_four") >= 6
