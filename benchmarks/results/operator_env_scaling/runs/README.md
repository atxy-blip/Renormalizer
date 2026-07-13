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
