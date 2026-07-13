#!/usr/bin/env python3
"""Merge Slurm per-point SOP vs TTNO benchmark CSV files.

The Slurm array script writes one CSV per parameter point under
``benchmarks/results/slurm_points``.  This utility merges successful point files
into the aggregate CSV names consumed by ``create_sop_vs_ttno_notebook.py``.
"""

from pathlib import Path

import pandas as pd

RESULT_DIR = Path(__file__).resolve().parent / "results"
POINT_DIR = RESULT_DIR / "slurm_points"
OUTPUTS = {
    "lead": RESULT_DIR / "lead_scaling.csv",
    "phonon": RESULT_DIR / "phonon_scaling.csv",
    "shared-structure": RESULT_DIR / "shared_structure_scaling.csv",
}


def _sort_frame(df: pd.DataFrame, case: str) -> pd.DataFrame:
    if case == "lead":
        return df.sort_values(["n_lead", "n_phonon"], kind="stable")
    if case == "phonon":
        return df.sort_values(["n_phonon", "n_lead"], kind="stable")
    return df.sort_values(["rank", "size"], kind="stable")


def main() -> None:
    frames = []
    for path in sorted(POINT_DIR.glob("*.csv")):
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            print(f"Skipping empty CSV: {path}")
            continue
        if frame.empty or "case" not in frame:
            print(f"Skipping invalid CSV: {path}")
            continue
        frame["source_csv"] = path.name
        frames.append(frame)

    if not frames:
        raise SystemExit(f"No point CSV files found in {POINT_DIR}")

    all_df = pd.concat(frames, ignore_index=True)
    for case, output in OUTPUTS.items():
        case_df = all_df[all_df["case"] == case].copy()
        if case_df.empty:
            print(f"No rows for {case}; not writing {output}")
            continue
        case_df = _sort_frame(case_df, case)
        drop_cols = [col for col in ["source_csv"] if col in case_df]
        case_df.drop(columns=drop_cols).to_csv(output, index=False)
        print(f"Wrote {output} ({len(case_df)} rows)")


if __name__ == "__main__":
    main()
