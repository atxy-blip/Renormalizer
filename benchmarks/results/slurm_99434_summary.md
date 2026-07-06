# Slurm 99434 SOP vs TTNO Results

Merged per-point CSV files from `benchmarks/results/slurm_points/` and regenerated `benchmarks/results/sop_vs_ttno_summary.ipynb`.

## Coverage

- Slurm array logs found: 37
- Per-point CSV files found: 33
- Merged rows: lead 5, phonon 7, shared-structure 21

## Failed Or Problematic Points

| task | case | output | status | elapsed (s) | max RSS (GB) | OOM | csv exists |
|---:|---|---|---:|---:|---:|---|---|
| 5 | lead | `lead_nlead16_phonon2.csv` | 137 | 530.3 | 127.8 | True | False |
| 6 | lead | `lead_nlead24_phonon2.csv` | 137 | 270.0 | 127.8 | True | False |
| 7 | lead | `lead_nlead32_phonon2.csv` | 137 | 315.8 | 127.8 | True | False |
| 14 | phonon | `phonon_lead4_nphonon24.csv` | 137 | 192.6 | 127.8 | True | False |
| 15 | phonon | `phonon_lead4_nphonon32.csv` | 0 | 188.4 | 120.3 | True | True |

## Lead Scaling

| n_lead | sites | terms | TTNO max bond | SOP apply (s) | TTNO apply (s) | speedup | rel err | peak SOP GB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 16 | 6 | 0.02163 | 0.00161 | 13.44 | 2.63e-17 | 0.00 |
| 2 | 12 | 32 | 7 | 0.05106 | 0.001864 | 27.39 | 0.00e+00 | 0.01 |
| 4 | 20 | 56 | 7 | 0.1661 | 0.002901 | 57.26 | 1.62e-08 | 0.09 |
| 8 | 36 | 104 | 7 | 0.9004 | 0.004886 | 184.3 | 0.00e+00 | 1.98 |
| 12 | 52 | 152 | 7 | 7.448 | 0.007181 | 1037 | 1.18e-08 | 10.04 |

## Phonon Scaling

| n_phonon | sites | terms | TTNO max bond | SOP apply (s) | TTNO apply (s) | speedup | rel err | peak SOP GB | status |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 19 | 52 | 7 | 0.1304 | 0.002596 | 50.23 | 1.27e-16 | 0.06 | ok |
| 2 | 20 | 56 | 7 | 0.1587 | 0.002692 | 58.95 | 1.62e-08 | 0.09 | ok |
| 4 | 22 | 64 | 7 | 0.2061 | 0.003006 | 68.56 | 0.00e+00 | 0.11 | ok |
| 8 | 26 | 80 | 7 | 0.4042 | 0.00344 | 117.5 | 9.89e-09 | 0.39 | ok |
| 12 | 30 | 96 | 7 | 0.7341 | 0.004104 | 178.9 | 0.00e+00 | 0.66 | ok |
| 16 | 34 | 112 | 7 | 1.253 | 0.004234 | 296 | 0.00e+00 | 2.12 | ok |
| 32 |  |  |  | nan | nan | nan | nan | nan | error: MemoryError: Unable to allocate 5.50 TiB for an array with shape (11534336, 65536) and data type float64 |

## Shared-Structure Stress Test

### Rank 1

| size | terms | TTNO max bond | TTNO elements | SOP apply (s) | TTNO apply (s) | speedup | rel err | peak SOP GB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 16 | 4 | 280 | 0.02072 | 0.00135 | 15.36 | 0.00e+00 | 0.00 |
| 6 | 36 | 6 | 612 | 0.06572 | 0.002162 | 30.39 | 0.00e+00 | 0.01 |
| 8 | 64 | 8 | 1028 | 0.1746 | 0.00223 | 78.31 | 0.00e+00 | 0.10 |
| 10 | 100 | 10 | 1688 | 0.6363 | 0.003004 | 211.8 | 0.00e+00 | 0.61 |
| 12 | 144 | 12 | 2532 | 2.037 | 0.004324 | 471 | 0.00e+00 | 2.12 |
| 14 | 196 | 14 | 3580 | 12.52 | 0.004327 | 2894 | 2.48e-09 | 8.40 |
| 16 | 256 | 16 | 4876 | 51.41 | 0.004022 | 1.278e+04 | 8.16e-09 | 36.43 |

### Rank 2

| size | terms | TTNO max bond | TTNO elements | SOP apply (s) | TTNO apply (s) | speedup | rel err | peak SOP GB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 16 | 4 | 280 | 0.02106 | 0.001611 | 13.07 | 0.00e+00 | 0.00 |
| 6 | 36 | 6 | 612 | 0.0669 | 0.001998 | 33.49 | 0.00e+00 | 0.01 |
| 8 | 64 | 8 | 1028 | 0.2258 | 0.002689 | 84 | 0.00e+00 | 0.10 |
| 10 | 100 | 10 | 1688 | 0.6665 | 0.003532 | 188.7 | 0.00e+00 | 0.61 |
| 12 | 144 | 12 | 2532 | 1.963 | 0.00393 | 499.4 | 0.00e+00 | 2.12 |
| 14 | 196 | 14 | 3580 | 10.41 | 0.004148 | 2509 | 2.31e-09 | 8.40 |
| 16 | 256 | 16 | 4876 | 51.05 | 0.003997 | 1.277e+04 | 0.00e+00 | 36.43 |

### Rank 4

| size | terms | TTNO max bond | TTNO elements | SOP apply (s) | TTNO apply (s) | speedup | rel err | peak SOP GB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 16 | 4 | 280 | 0.02106 | 0.001643 | 12.81 | 0.00e+00 | 0.00 |
| 6 | 36 | 6 | 612 | 0.06573 | 0.00205 | 32.06 | 0.00e+00 | 0.01 |
| 8 | 64 | 8 | 1028 | 0.1622 | 0.002298 | 70.57 | 0.00e+00 | 0.10 |
| 10 | 100 | 10 | 1688 | 0.6399 | 0.003244 | 197.3 | 0.00e+00 | 0.61 |
| 12 | 144 | 12 | 2532 | 1.843 | 0.003886 | 474.2 | 4.40e-09 | 2.12 |
| 14 | 196 | 14 | 3580 | 12.7 | 0.004322 | 2939 | 3.53e-09 | 8.40 |
| 16 | 256 | 16 | 4876 | 54.76 | 0.004083 | 1.341e+04 | 4.47e-09 | 36.43 |

## Interpretation

- Maximum relative apply error among successful rows: `1.616e-08`.
- Maximum expectation error among successful rows: `2.776e-16`.
- Lead scaling completed through `n_lead=12`; `n_lead=16/24/32` exceeded the 128 GB memory request before writing CSV.
- Phonon scaling completed through `n_phonon=16`; `n_phonon=24` was OOM-killed and `n_phonon=32` produced a captured MemoryError row.
- Shared-structure completed through `size=16` for ranks 1, 2, and 4. This is the clearest operator-count stress trend: SOP apply time grows from about 0.02 s at size 4 to about 50 s at size 16, while TTNO apply stays near 0.001-0.004 s.
- The large-memory failures are caused by large intermediate materialization in the current benchmark path, including dense-state checks for some large physical dimensions and tensor-contraction intermediates such as the `phonon=32` `oe.contract` allocation. The successful rows remain useful for trends, but larger lead/phonon points need non-dense validation and/or a higher-memory job.

## Generated Artifacts

- `benchmarks/results/lead_scaling.csv`
- `benchmarks/results/phonon_scaling.csv`
- `benchmarks/results/shared_structure_scaling.csv`
- `benchmarks/results/sop_vs_ttno_summary.ipynb`
- `benchmarks/results/fig_*.png`
