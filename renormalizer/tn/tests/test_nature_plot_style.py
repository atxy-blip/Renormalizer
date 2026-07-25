import matplotlib.pyplot as plt

from benchmarks.nature_plot_style import (
    METHOD_STYLES,
    NATURE_RCPARAMS,
    nature_style,
    save_pdf_png,
)


def test_nature_style_matches_repository_contract():
    assert NATURE_RCPARAMS["font.sans-serif"] == ["Arial", "Helvetica", "DejaVu Sans"]
    assert NATURE_RCPARAMS["pdf.fonttype"] == 42
    assert NATURE_RCPARAMS["font.size"] == 8
    assert NATURE_RCPARAMS["axes.linewidth"] == 0.8
    assert NATURE_RCPARAMS["lines.linewidth"] == 1.2
    assert NATURE_RCPARAMS["xtick.direction"] == "in"
    assert NATURE_RCPARAMS["xtick.top"] is True
    assert METHOD_STYLES["sop_no_env"]["color"] == "#00529B"
    assert METHOD_STYLES["sop_mctdh_like_state_env"]["color"] == "#CC0000"
    assert METHOD_STYLES["ttno_with_env"]["color"] == "#007A33"


def test_save_pdf_png_writes_both_fixed_boundary_outputs(tmp_path):
    with nature_style():
        fig, ax = plt.subplots(figsize=(3.5, 2.8))
        ax.plot([1, 2], [1, 2])
        pdf, png = save_pdf_png(fig, tmp_path / "figure.pdf")
    assert pdf.name == "figure.pdf"
    assert png.name == "figure.png"
    assert pdf.stat().st_size > 0
    assert png.stat().st_size > 0
