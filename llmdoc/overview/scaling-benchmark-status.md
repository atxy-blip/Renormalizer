# Operator scaling benchmark 当前状态

本页是 `feat/mctdh-sop-comparison` 分支的当前进度入口。历史实验仍保留，
但当前正式结论来自 contraction diagnostics 和 Li.W.2024 spin-boson rerun。

## 已提交基线

commit `7c974c0 Update benchmarks` 已包含：

- flat `sop_no_env`、strict `sop_mctdh_like_state_env` 和
  `ttno_with_env` 的 all-node one-site local-action benchmark；
- recoverable per-task NPZ snapshot infrastructure；
- Hubbard-junction `ren_formal` partial result。

Hubbard-junction formal array 仍冻结在 204/216：

```text
missing:
  modes / sop_no_env / N_total_sites=300: 3 repeats
  state_bond / all methods / M_s=300: 9 repeats
```

它是历史诊断数据源，不是当前 Li.W.2024 模型的正式结果。

## Contraction diagnostics

结果目录：

```text
benchmarks/results/operator_env_scaling/contraction_diagnostics/
```

状态：

```text
tasks: 144 / 144
status: all ok
repeats: 3
```

该实验分离 shape-only optimized FLOPs、isolated dense-kernel wall time 和
Hubbard-junction full-model timing。主要结论：

```text
internal state-bond FLOPs:
  SOP internal  = 6 M_s^4
  TTNO internal = 48 M_s^4 + 128 M_s^2

paired two-mode leaf:
  FLOPs         = 160 d^4 + 3200 d^2
  TTNO elements = 32 d^4 + 1354

primitive-contracted one-mode leaves:
  FLOPs         = 160 d^2 + 3200 d
  TTNO elements = 48 d^2 + 1642
```

internal-node wall time 在测试区间内小于四次方，但 largest-four-point 指数已从
全区间的约 2.90/3.18 上升到约 3.63/3.81。数学 FLOP 次数与有限尺寸 wall-time
指数必须分开报告。

Nature-style artifact pair（每张固定版式图均同时保存 transparent PDF 和
300-dpi PNG）：

```text
benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/
  complexity_validation.pdf
  complexity_validation.png
  model_mechanism.pdf
  model_mechanism.png
```

## Li.W.2024 spin-boson rerun

结果目录：

```text
benchmarks/results/operator_env_scaling/li2024_formal/
benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_*
```

状态：

```text
tasks: 189 / 189
status: all ok
max relative error vs TTNO: 1.61414e-15
quantity: local_effective_1site_apply_all_nodes
```

模型采用 sub-Ohmic spin-boson 参数 `s=0.5`, `omega_c=20 Delta`,
`alpha=0.05`, `Delta=1` 和 `SpectralDensityFunction.Wang1` 离散化。
每个 panel、方法和参数点各有 3 个 repeat。

### 正式解释口径（2026-08-06）

正文图 `li2024_spin_boson_20260713_scaling_three_panel.{pdf,png}`：

- `modes` panel 是唯一报 scaling 指数的面板（largest-four fit）：

| 方法 | N_b exponent |
| --- | ---: |
| `sop_no_env` | 3.109 |
| `sop_mctdh_like_state_env` | 2.035 |
| `ttno_with_env` | 0.916 |

对应 `N_b^3 / N_b^2 / N_b` 的 state/operator reuse 结构。

- `state_bond` 与 `primitive_basis` panel 只作参数稳健性检查：不报指数、
  不画幂次参考线；三条方法相对排名在每个参数点稳定（TTNO 最快，strict
  state env 次之，no env 最慢）；两个 panel 均标注 adaptive topology switch
  （d > M_s：paired ↔ contracted），跳变来自 leaf 数翻倍与 d^4 → d^2 切换，
  详见 `llmdoc/architecture/paired-vs-contracted-leaves.md`。

指数与幂次参考线完整保留在 SI：

```text
benchmarks/results/operator_env_scaling/final/
  li2024_spin_boson_20260713_si_scaling_three_panel.pdf
  li2024_spin_boson_20260713_si_scaling_three_panel.png
  li2024_spin_boson_20260713_si_fits.csv
```

SI 图中 M_s panel 保留 M_s^4 参考线，大 d panel 保留常数参考线。它们是有效
wall-time 指数与参考线，不是渐近 FLOP 指数；isolated full-rank internal
contraction 的 FLOP 仍为精确 M_s^4（见 contraction diagnostics）。

刻意边界：

- 本 benchmark 只测量 `local_effective_1site_apply_all_nodes` kernel，不做
  完整 TDVP/传播 step 计时；这是有意的窄口径对比，不是缺口。
- 不扩大 M_s 区间；不做 M_s 时间占比/throughput 分解。

### 再生成方式

所有 main/SI artifacts 由现有 189 个 snapshots 经 Slurm finalizer 生成，
不重跑 benchmark：

```bash
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```

## 科学表述边界

- 三条路径比较的是相同的 all-node one-site local effective action。
- 它们不是 Li.W.2024 或 Ren.J.2022 中完整 TDVP propagation step 的直接计时。
- isolated full-rank internal contraction 是 `M_s^4` FLOPs；当前完整 benchmark
  的约 2.2 wall-time exponent 是有限参数区间内的有效指数。
- 旧 paired-leaf `d^4` 已定位为 tree grouping 导致的 dense tensor shape，
  不是 TTNO 表示普遍必须具有的 `d^4` 复杂度。

## 仍待决定

1. 将旧 204/216 Hubbard-junction formal array 标为永久 partial archive，或补齐 12 个任务。

已决定（2026-08-06）：不做完整 TDVP step benchmark；不扩大 `M_s` 区间；
不做 `M_s` 时间占比/throughput 分解。
