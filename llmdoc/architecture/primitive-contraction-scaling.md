# Primitive contraction 与缩并标度

本文记录 phonon leaf grouping 如何决定 TTNS/TTNO 的 primitive-basis 标度。

## 两种 tree layout

`BasisTree.binary_mctdh(..., contract_primitive=False)` 会把两个 primitive modes
放在同一个 bottom leaf。对 state bond `M`、operator bond `O` 和每个 mode 的
primitive dimension `d`：

```text
state leaf shape:    (M, d, d)
operator leaf shape: (O, d, d, d, d)
```

operator leaf 有两个输入和两个输出 physical axes，因此仅 dense operator storage
就包含 `O d^4` 个元素。

`contract_primitive=True` 会把 primitive modes 拆成一 mode 一 leaf：

```text
state leaf shape:    (M, d)
operator leaf shape: (O, d, d)
```

operator storage 变为 `O d^2`。这不是低阶拟合差异，而是 tensor rank 和 physical
axis 数发生了变化。

## 诊断中的精确公式

当前 diagnostic 固定 `M=20`, `O=4`。`opt_einsum` 将乘法和加法各计一个 FLOP：

```text
paired leaf:
  F(d) = 160 d^4 + 3200 d^2

primitive-contracted leaf:
  F(d) = 160 d^2 + 3200 d
```

Hubbard-junction full-model TTNO 元素数为：

```text
paired tree:
  N_TTNO(d) = 32 d^4 + 1354

primitive-contracted tree:
  N_TTNO(d) = 48 d^2 + 1642
```

paired tree 在 `d=100` 时约有 32 亿个 TTNO 元素，double precision 原始数据约
25.6 GB；实测 peak resident memory 约 27.7 GB。operator construction、
environment construction、local action 和 total time 的大 `d` tail 都接近四次方，
所以 `d^4` 不是单一 timer 或 TTNO construction 计时造成的假象。

## Adaptive topology

Li.W.2024 spin-boson benchmark 使用：

```text
contract_primitive = (d > M_s)
```

当 primitive basis 大于 state bond 时，先在 primitive layer 收缩可避免把 `d^2`
作为一个 composite physical space带入 body tree。`d == M_s` 不启用 contraction，
因为此时没有 basis compression 收益。

切换 topology 会同时改变 active-node 数和固定内部工作。因此大 `d` whole-model
wall time 近似常数，只能说明新增 `d^2` leaf work 尚未超过固定 body-tree work；
不能把 isolated leaf complexity 写成 `O(1)`。

## State-bond 诊断

对 full-rank binary internal node，diagnostic 得到：

```text
SOP internal:
  F(M_s) = 6 M_s^4

TTNO internal, O=4:
  F(M_s) = 48 M_s^4 + 128 M_s^2
```

shape-only optimized FLOPs 精确恢复四次方。有限尺寸 wall time 会受到调用开销、
lower-order work 和 BLAS throughput 随尺寸提升的影响，因此 all-point 或完整树
计时可显著低于 4。报告时应区分：

- tensor-index / optimized-FLOP complexity；
- isolated kernel wall-time exponent；
- full all-node workflow wall-time exponent。

## 代码入口

- `benchmarks/benchmark_adaptive_operator_env.py`
  (`build_hubbard_junction_case`): `phonon_contract_primitive` 开关。
- `benchmarks/benchmark_li2024_operator_env.py`: spin-boson model 和 adaptive tree。
- `benchmarks/contraction_scaling_diagnostics.py`: manifest 和 shape-only path metrics。
- `benchmarks/run_contraction_scaling_diagnostic.py`: isolated/full-model runner。
- `benchmarks/results/operator_env_scaling/contraction_diagnostics/analysis.md`:
  完整数值分析。
