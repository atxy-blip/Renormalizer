# New Runs

The active Slurm wrapper writes new raw CSV, fit CSV, and logs here. A run is
promoted to `../final/` only after its timing object, method identity,
correctness, and scaling range have been reviewed. Superseded runs move to one
of the semantic archive directories.

## 2026-07-12 recoverable three-variable runs

All jobs use `ACTIVE_SCOPE=all_nodes`, three repeats, one CPU thread, and no
adaptive extra point. The benchmark checkpoints raw rows after every repeat
and fits after every completed point.

| Job | Scaling path | Explicit scan | Fixed parameters |
| --- | --- | --- | --- |
| 114776 | `lead_only` | `n_lead = 4, 8, 16` | `n_phonon = 0` |
| 114777 | `lead_only` | `n_lead = 32` | `n_phonon = 0` |
| 114778 | `state_bond` | `M_s = 4, 8, 16, 32, 64` | `n_lead = 4`, `n_phonon = 0` |
| 114779 | `primitive_basis` | `d = 4, 8, 16, 32` | `n_lead = 1`, `n_phonon = 16`, `M_s = 16` |

The site-number path is split because the strict no-environment cost at
`n_lead = 32` is already several hours for three repeats. `n_lead >= 64` is
not included in this 12-hour batch.

## 2026-07-13 Ren-style formal Tree array

The formal experiment is stored under `../ren_formal/` and uses independent
NPZ snapshots rather than an end-of-job CSV.

```text
manifest: ../ren_formal/manifest.tsv
tasks: 216 = 24 parameter points * 3 methods * 3 repeats
failed/cancelled array: 114789 (runner invoked by file path; package import failed)
active replacement array: 115005
```

Parameter controls follow Ren.J.2022 Figure 10 while retaining the existing
Tree SOP/TTNO algorithms:

```text
modes:          M_s=20, d=10, N_total_sites=18,30,46,74,118,186,300
state_bond:     N_b=16, d=10, M_s=10,20,30,50,70,100,150,220,300
primitive_basis:N_b=16, M_s=20, d=5,10,20,30,40,50,70,100
```

## 2026-07-13 contraction-complexity diagnostics

This experiment separates the contraction count from whole-model timing and
then changes only the phonon-leaf grouping in the actual Hubbard-junction
model.  Each parameter point has three independent Slurm tasks.

```text
manifest: ../contraction_diagnostics/manifest.tsv
tasks: 144 = 6 controls * 8 parameter values * 3 repeats
initial array: 115387 (tasks 0--7 completed; tasks 8--143 failed during conda
               activation because nounset was enabled too early)
replacement array: 115549 (tasks 8--143 only)
dependent aggregation: 115555 (afterany:115549)
```

Final status:

```text
snapshots: 144 / 144, all status=ok
missing tasks: 0
analysis: ../contraction_diagnostics/analysis.md
figures: ../contraction_diagnostics/figures/
```

The six controls are:

```text
internal M_s: SOP internal kernel, TTNO internal kernel
leaf d:       paired TTNO leaf, primitive-contracted TTNO leaf
model d:      paired Hubbard-junction tree, primitive-contracted tree
```

The shape-only optimized-FLOP fits test the mathematical exponents directly.
The dense-kernel timings test whether the large-size tail approaches those
exponents, while the model controls record TTNS/TTNO leaf shapes, tensor
element counts, construction/environment/expression/apply times, and peak
resident memory.  Aggregation takes the median across repeats and reports both
all-point and largest-four-point log--log fits.  A missing-task list is written
even when an array member fails.

## 2026-07-13 Li.W.2024 spin--boson rerun

This rerun replaces the earlier Hubbard-junction formal setup with the
sub-Ohmic spin--boson Hamiltonian and adaptive binary tree described around
Figs. 4 and 6 of Li.W.2024.  It retains the repository's three operator paths
and explicitly labels the measured quantity as the all-node one-site local
effective-Hamiltonian action, not a complete TDVP-PS step.

```text
result root: ../li2024_formal/
manifest: ../li2024_formal/manifest.tsv
tasks: 189 = 21 points * 3 methods * 3 repeats
compute-node smoke: 115694 (task 0, COMPLETED, exit 0:0)
production array: 115695 (tasks 1--188, maximum 12 concurrent)
dependent finalizer: 115708 (afterany:115695)
```

Controls and topology:

```text
N_b panel: M_s=20, d=10, N_b=4 8 16 32 64 128 256
M_s panel: N_b=16, d=10, M_s=4 8 16 32 50 70 100
d panel:   N_b=16, M_s=20, d=4 8 16 32 50 70 100
primitive contraction: enabled exactly when d > M_s
```

The finalizer refuses to create a final PDF unless all 189 task IDs have an
`ok` snapshot.  On complete input it writes:

```text
../li2024_formal/li2024_formal_raw.csv
../li2024_formal/missing_or_error_tasks.json
../final/li2024_spin_boson_20260713_summary.csv
../final/li2024_spin_boson_20260713_fits.csv
../final/li2024_spin_boson_20260713_scaling_three_panel.pdf
```
