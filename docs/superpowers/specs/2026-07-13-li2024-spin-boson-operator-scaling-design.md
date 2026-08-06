# Li.W.2024 Spin--Boson Operator Scaling Design

> **2026-08-06 修订**：plot contract 已更新——正文图只对 `modes` panel 报
> scaling 指数（`N_b^3/N_b^2/N_b`）；`state_bond` 与 `primitive_basis` panel
> 在正文以参数稳健性呈现（不报指数、不画幂次参考线，标注 topology switch）；
> 全部 panel 的指数与幂次参考线保留在 SI（`*_si_fits.csv`、
> `*_si_scaling_three_panel.*`）。实现见
> `docs/superpowers/plans/2026-08-06-operator-scaling-narrative-refactor.md`。

## Goal

Replace the earlier Hubbard-junction formal scan with an isolated benchmark
that uses the spin--boson model and adaptive binary-tree setup described around
Figs. 4 and 6 of Li.W.2024, while retaining the repository's three operator
paths for a controlled comparison.

## Scientific identity

The measured quantity remains the all-node collection of one-site local
effective-Hamiltonian actions.  It is the common kernel implemented by
`sop_no_env`, `sop_mctdh_like_state_env`, and `ttno_with_env`; it is not labeled
as the paper's complete TDVP-PS evolution step.

The Hamiltonian uses the paper's sub-Ohmic spin--boson parameters
`s=0.5`, `omega_c=20 Delta`, `alpha=0.05`, and `Delta=1`.  Wang's first
discretization already implemented in `SpectralDensityFunction.Wang1` supplies
the mode frequencies and couplings.

## Parameter controls

The binary-tree scans use three repeats per method and point:

- modes: `M_s=20`, `d=10`, `N_b=4,8,16,32,64,128,256`;
- state bond: `N_b=16`, `d=10`, `M_s=4,8,16,32,50,70,100`;
- primitive basis: `N_b=16`, `M_s=20`, `d=4,8,16,32,50,70,100`.

Every manifest row records the topology choice.  Primitive contraction is
enabled exactly when `d > M_s`; otherwise two primitive modes are attached to
each binary leaf.  Equality uses no contraction because it provides no basis
compression.

## Outputs and recovery

Each `(panel, method, point, repeat)` is one Slurm array task and atomically
writes a JSON-backed NPZ under
`benchmarks/results/operator_env_scaling/li2024_formal/snapshots/`.  A dependent
finalizer writes the raw CSV, missing/error task report, repeat summary, fit
table, and three-panel PDF.  Existing `ren_formal` snapshots and the partial
2026-07-13 PDF remain untouched.

## Plot contract

The modes panel retains the operator-path guides `N_b^3`, `N_b^2`, and `N_b`
for no-env SOP, strict state-env SOP, and bounded-bond TTNO.  The state-bond
panel uses `M_s^4` guides, matching the full-rank binary internal-node FLOP
count.  The large-`d` panel uses constant guides for all three paths because
the adaptive binary tree contracts each primitive basis before the expensive
body nodes once `d > M_s`.

## Validation

Tests fix the exact manifest, topology switch, spin--boson term count and tree
shape, snapshot serialization, reference exponents, and safe Slurm activation
order.  A small all-node method run checks numerical agreement with TTNO before
the production array is submitted.
