"""Shared plotting and export helpers for formal benchmark figures."""

from pathlib import Path

import matplotlib


NATURE_RCPARAMS = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.2,
    "lines.markersize": 4.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


METHOD_STYLES = {
    "sop_no_env": {"color": "#00529B", "marker": "o"},
    "sop_mctdh_like_state_env": {
        "color": "#CC0000",
        "marker": "o",
        "markerfacecolor": "none",
    },
    "ttno_with_env": {"color": "#007A33", "marker": "s"},
}


def nature_style():
    """Return the repository's scoped Matplotlib Nature-style settings."""
    return matplotlib.rc_context(NATURE_RCPARAMS)


def finish_axis(ax, *, minor=True):
    """Apply the common inward tick treatment to an axis."""
    ax.tick_params(which="major", direction="in", length=4, width=0.8, top=True, right=True)
    ax.tick_params(which="minor", direction="in", length=2, width=0.6, top=True, right=True)
    if minor:
        ax.minorticks_on()


def label_panel(ax, label: str, title: str):
    """Set a concise, left-aligned panel label and title."""
    ax.set_title(f"({label}) {title}", loc="left")


def save_pdf_png(fig, pdf_path: Path, *, dpi: int = 300):
    """Save fixed-boundary transparent PDF and PNG versions of a figure."""
    pdf_path = Path(pdf_path)
    png_path = pdf_path.with_suffix(".png")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(pdf_path, format="pdf", transparent=True)
    fig.savefig(png_path, format="png", dpi=dpi, transparent=True)
    return pdf_path, png_path
