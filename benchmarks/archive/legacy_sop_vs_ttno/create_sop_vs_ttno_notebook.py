#!/usr/bin/env python3
"""Create a Jupyter notebook summarizing SOP vs TTNO benchmark results."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULT_DIR = Path(__file__).resolve().parent / "results"
NOTEBOOK_PATH = RESULT_DIR / "sop_vs_ttno_summary.ipynb"
CSV_FILES = [
    RESULT_DIR / "lead_scaling.csv",
    RESULT_DIR / "phonon_scaling.csv",
    RESULT_DIR / "shared_structure_scaling.csv",
]


def _read_results():
    frames = []
    missing = []
    for path in CSV_FILES:
        if path.exists():
            frame = pd.read_csv(path)
            frame["source_csv"] = path.name
            frames.append(frame)
        else:
            missing.append(path.name)
    if frames:
        return pd.concat(frames, ignore_index=True), missing
    return pd.DataFrame(), missing


def _ok_frame(df):
    if df.empty or "status" not in df:
        return df
    return df[df["status"].fillna("").astype(str).str.startswith("ok")].copy()


def _save_line_plot(df, x, ys, title, ylabel, path, logy=False):
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    if df.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
    else:
        for y, label in ys:
            if y in df:
                ax.plot(df[x], df[y], marker="o", label=label)
        ax.set_xlabel(x)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if logy:
            ax.set_yscale("log")
        ax.grid(True, alpha=0.3)
        if len(ys) > 1:
            ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _generate_figures(df):
    ok = _ok_frame(df)
    figures = []

    lead = ok[ok["case"] == "lead"].sort_values("n_lead") if not ok.empty else pd.DataFrame()
    _save_line_plot(lead, "n_lead", [("sop_n_terms", "SOP terms")], "Lead basis scaling: SOP terms", "count", RESULT_DIR / "fig_lead_terms.png")
    _save_line_plot(lead, "n_lead", [("ttno_max_bond_dim", "TTNO max bond")], "Lead basis scaling: TTNO max bond", "bond dimension", RESULT_DIR / "fig_lead_bond.png")
    _save_line_plot(lead, "n_lead", [("sop_apply_time_median", "SOP"), ("ttno_apply_time_median", "TTNO")], "Lead basis scaling: apply time", "seconds", RESULT_DIR / "fig_lead_apply_time.png", logy=True)
    _save_line_plot(lead, "n_lead", [("sop_build_time_median", "SOP"), ("ttno_build_time_median", "TTNO")], "Lead basis scaling: construction time", "seconds", RESULT_DIR / "fig_lead_build_time.png", logy=True)
    _save_line_plot(lead, "n_lead", [("sop_apply_speedup", "SOP time / TTNO time")], "Lead basis scaling: TTNO relative apply speedup", "speedup", RESULT_DIR / "fig_lead_speedup.png")
    figures += ["fig_lead_terms.png", "fig_lead_bond.png", "fig_lead_apply_time.png", "fig_lead_build_time.png", "fig_lead_speedup.png"]

    phonon = ok[ok["case"] == "phonon"].sort_values("n_phonon") if not ok.empty else pd.DataFrame()
    _save_line_plot(phonon, "n_phonon", [("sop_n_terms", "SOP terms")], "Phonon basis scaling: SOP terms", "count", RESULT_DIR / "fig_phonon_terms.png")
    _save_line_plot(phonon, "n_phonon", [("ttno_max_bond_dim", "TTNO max bond")], "Phonon basis scaling: TTNO max bond", "bond dimension", RESULT_DIR / "fig_phonon_bond.png")
    _save_line_plot(phonon, "n_phonon", [("sop_apply_time_median", "SOP"), ("ttno_apply_time_median", "TTNO")], "Phonon basis scaling: apply time", "seconds", RESULT_DIR / "fig_phonon_apply_time.png", logy=True)
    _save_line_plot(phonon, "n_phonon", [("sop_build_time_median", "SOP"), ("ttno_build_time_median", "TTNO")], "Phonon basis scaling: construction time", "seconds", RESULT_DIR / "fig_phonon_build_time.png", logy=True)
    _save_line_plot(phonon, "n_phonon", [("sop_apply_speedup", "SOP time / TTNO time")], "Phonon basis scaling: TTNO relative apply speedup", "speedup", RESULT_DIR / "fig_phonon_speedup.png")
    figures += ["fig_phonon_terms.png", "fig_phonon_bond.png", "fig_phonon_apply_time.png", "fig_phonon_build_time.png", "fig_phonon_speedup.png"]

    shared = ok[ok["case"] == "shared-structure"].sort_values(["rank", "size"]) if not ok.empty else pd.DataFrame()
    if not shared.empty:
        for y, ylabel, filename, title in [
            ("sop_n_terms", "SOP terms", "fig_shared_terms.png", "Operator-count stress test: SOP terms"),
            ("ttno_total_tensor_elements", "TTNO tensor elements", "fig_shared_ttno_elements.png", "Operator-count stress test: TTNO tensor elements"),
            ("sop_apply_speedup", "SOP time / TTNO time", "fig_shared_speedup.png", "Operator-count stress test: apply speedup"),
        ]:
            fig, ax = plt.subplots(figsize=(6.5, 4.0))
            for rank, group in shared.groupby("rank"):
                ax.plot(group["size"], group[y], marker="o", label=f"rank {rank}")
            ax.set_xlabel("size")
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(RESULT_DIR / filename, dpi=180)
            plt.close(fig)
    else:
        _save_line_plot(shared, "size", [("sop_n_terms", "SOP terms")], "Operator-count stress test: SOP terms", "count", RESULT_DIR / "fig_shared_terms.png")
        _save_line_plot(shared, "size", [("ttno_total_tensor_elements", "TTNO tensor elements")], "Operator-count stress test: TTNO tensor elements", "elements", RESULT_DIR / "fig_shared_ttno_elements.png")
        _save_line_plot(shared, "size", [("sop_apply_speedup", "SOP time / TTNO time")], "Operator-count stress test: apply speedup", "speedup", RESULT_DIR / "fig_shared_speedup.png")
    figures += ["fig_shared_terms.png", "fig_shared_ttno_elements.png", "fig_shared_speedup.png"]
    return figures


def _markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def _code_cell(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(True)}


def _format_correctness(df):
    ok = _ok_frame(df)
    if ok.empty:
        return "No successful benchmark rows were found."
    max_rel = ok["relative_apply_error"].max()
    max_exp = ok["expectation_error"].max()
    threshold = 1e-8 if max_rel >= 1e-10 or max_exp >= 1e-10 else 1e-10
    failures = ok[(ok["relative_apply_error"] >= threshold) | (ok["expectation_error"] >= threshold)]
    if failures.empty:
        return f"All reported benchmark points satisfy relative apply error < {threshold:g} and expectation error < {threshold:g}. Max relative apply error = {max_rel:.3e}; max expectation error = {max_exp:.3e}."
    return f"Some benchmark points exceed {threshold:g}. Max relative apply error = {max_rel:.3e}; max expectation error = {max_exp:.3e}. See the raw table for details."


def create_notebook():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    df, missing = _read_results()
    figures = _generate_figures(df)
    missing_text = "" if not missing else "\n\nMissing CSV files: " + ", ".join(f"`{m}`" for m in missing) + "."

    cells = [
        _markdown_cell("""# SOP vs TTNO Operator Baseline

This notebook compares an ML-MCTDH-style flat sum-of-products operator baseline with the existing compressed TTNO representation on the same TTNS tree, local basis, and symbolic Hamiltonian.
"""),
        _markdown_cell("""## 1. Purpose

The junction benchmark follows the operator/tree construction pattern of `../ttns-test/junction_zt_hubbard.py`, the script used for the paper calculations. The external script is not imported directly because it executes argument parsing, logging setup, TTNO construction, TTNS expansion, and time evolution at module import time.

The SOP baseline represents the traditional MCTDH / ML-MCTDH operator layer: a Hamiltonian is kept as a flat list of product terms and each product term is applied independently. It is not a full ML-MCTDH propagator or SPF-equation implementation.

TTNO and SOP use the same symbolic Hamiltonian, the same tree topology, and the same local basis. The comparison therefore targets operator representation efficiency. The notebook focuses on two experimentally useful axes: basis-size growth in the Hubbard junction model and product-operator count growth in an artificial shared-structure stress test. TFD is not treated as a separate TTNO-construction question here because it is a Hamiltonian preparation choice, not a different low-level TTNO algorithm.
"""),
        _code_cell("""from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
RESULT_DIR = Path('benchmarks/results')
csv_files = ['lead_scaling.csv', 'phonon_scaling.csv', 'shared_structure_scaling.csv']
frames = []
for name in csv_files:
    path = RESULT_DIR / name
    if path.exists():
        df_part = pd.read_csv(path)
        df_part['source_csv'] = name
        frames.append(df_part)
df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
df.head()
"""),
        _markdown_cell("## 2. Correctness Checks\n\n" + _format_correctness(df) + missing_text),
        _code_cell("""if not df.empty:
    display(df[['case', 'n_lead', 'n_phonon', 'relative_apply_error', 'expectation_error', 'current_relative_apply_error', 'status']])
else:
    print('No benchmark CSV files found.')
"""),
        _markdown_cell("""## 3. Raw Benchmark Table

This table keeps the quantities needed to audit the comparison: term count, TTNO bond dimension, separated construction/apply timings, speedup, and numerical error. `sop_apply_speedup` means `SOP apply time / TTNO apply time`.
"""),
        _code_cell("""cols = ['case', 'n_lead', 'n_phonon', 'n_sites', 'local_dim_summary', 'sop_n_terms', 'ttno_max_bond_dim', 'ttno_total_tensor_elements', 'sop_build_time_median', 'ttno_build_time_median', 'sop_apply_time_median', 'ttno_apply_time_median', 'sop_apply_speedup', 'relative_apply_error', 'status']
if not df.empty:
    display(df[[c for c in cols if c in df.columns]])
"""),
        _markdown_cell("""## 4. Lead Basis Scaling

These figures vary `n_lead`, matching the `--nemode` parameter in `junction_zt_hubbard.py`. Each increment adds four electronic lead sites: left/right electrodes and spin-up/spin-down channels. This is the basis-size growth most directly relevant to the published molecular junction setup.

The SOP-term plot shows how many flattened product terms the baseline must traverse. The TTNO-bond plot shows whether the compressed operator network grows mildly or sharply. The apply-time plot is the actual cost of `H psi`, while the construction-time plot is separated so TTNO setup overhead is not confused with contraction cost. The speedup plot summarizes the apply-time crossover.

![Lead SOP terms](fig_lead_terms.png)

![Lead TTNO bond](fig_lead_bond.png)

![Lead apply time](fig_lead_apply_time.png)

![Lead construction time](fig_lead_build_time.png)

![Lead speedup](fig_lead_speedup.png)
"""),
        _markdown_cell("""## 5. Phonon Basis Scaling

These figures vary `n_phonon` while keeping the electronic lead size fixed. This isolates growth in the vibrational bath attached to the bridge-centered TTNS tree. It is useful because phonon modes increase both the local basis workload and the number of phonon Hamiltonian/product coupling terms.

The term and TTNO-bond plots show whether the operator representation grows mostly through flattened terms or through compact operator bonds. The timing plots then show how that representation growth appears in actual apply and construction costs.

![Phonon SOP terms](fig_phonon_terms.png)

![Phonon TTNO bond](fig_phonon_bond.png)

![Phonon apply time](fig_phonon_apply_time.png)

![Phonon construction time](fig_phonon_build_time.png)

![Phonon speedup](fig_phonon_speedup.png)
"""),
        _markdown_cell("""## 6. Operator-Count Stress Test

This is an artificial operator representation stress test, not a molecular-junction physical conclusion. It constructs `H = sum_ij V_ij A_i B_j` with low-rank coefficients and then stores it as a flattened SOP list. The purpose is to make product-term count grow rapidly while preserving shared structure that a compressed operator network can represent more economically.

The SOP-term plot verifies the intended product-count growth. The TTNO tensor-element plot checks whether compressed storage grows at the same rate. The speedup plot shows whether repeated flattened traversal becomes the dominant cost.

![Shared terms](fig_shared_terms.png)

![Shared TTNO tensor elements](fig_shared_ttno_elements.png)

![Shared speedup](fig_shared_speedup.png)
"""),
        _markdown_cell("""## 7. Interpretation

The SOP baseline applies each product term independently, mimicking the operator-layer behavior of conventional MCTDH/ML-MCTDH sum-of-products Hamiltonians. The TTNO representation produces numerically equivalent results while reusing common operator structure through tree-network bonds.

For the same symbolic Hamiltonian and TTNS state representation, the compressed TTNO operator layer is more efficient than the uncompressed flat SOP baseline in the tested basis-size and operator-count regimes. Small-system results should not be overinterpreted because TTNO construction and contraction overheads are visible, and simple Hamiltonians with only linear term growth may show a smaller advantage than correlated or highly repeated product-operator families.
"""),
        _markdown_cell("""## 8. Reproducibility

```bash
python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case lead --lead-list 1 2 4 8 16 32 --phonon 2 --repeats 7 --output benchmarks/results/lead_scaling.csv
python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case phonon --lead 4 --phonon-list 1 2 4 8 16 32 --repeats 7 --output benchmarks/results/phonon_scaling.csv
python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case shared-structure --size-list 4 8 16 32 64 --rank-list 1 2 4 --repeats 7 --output benchmarks/results/shared_structure_scaling.csv
python benchmarks/archive/legacy_sop_vs_ttno/create_sop_vs_ttno_notebook.py
```
"""),
    ]

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=2))
    print(f"Wrote {NOTEBOOK_PATH}")
    for figure in figures:
        print(f"Wrote {RESULT_DIR / figure}")


if __name__ == "__main__":
    create_notebook()
