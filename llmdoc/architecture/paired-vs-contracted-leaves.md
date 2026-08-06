# Paired vs Contracted 声子叶因子化

## 目的

解释 Li.W.2024 spin-boson benchmark 中两种声子叶因子化的结构、存储/FLOP
差异、自适应切换规则，以及切换造成的全模型 wall-time 跳变。避免把
“拓扑切换”误读为算法本身的复杂度变化。

## 两种布局

`contract_primitive = (d > M_s)` 决定 phonon tree 布局：

- `paired_no_contraction`（d <= M_s）
  - 每个 leaf 合并 2 个 primitive modes。
  - state leaf tensor shape：`(M_s, d, d)`。
  - TTNO leaf tensor shape：`(O, d, d, d, d)`，即 4 个 physical operator axes。
  - isolated leaf optimized FLOPs：`F(d) = 160 d^4 + 3200 d^2`；
    全树 TTNO 元素数：`N_TTNO(d) = 32 d^4 + 1354`。
- `primitive_contracted`（d > M_s）
  - 每个 leaf 只含 1 个 primitive mode。
  - state leaf tensor shape：`(M_s, d)`。
  - TTNO leaf tensor shape：`(O, d, d)`，即 2 个 physical operator axes。
  - isolated leaf optimized FLOPs：`F(d) = 160 d^2 + 3200 d`；
    全树 TTNO 元素数：`N_TTNO(d) = 48 d^2 + 1642`。

公式来源：`benchmarks/results/operator_env_scaling/contraction_diagnostics/analysis.md`
（shape-only optimized FLOPs 与 tensor storage 精确匹配，最大绝对偏差为零）。

## 为什么会有 d^4

paired leaf 的稠密 TTNO 张量把 d×d 的 primitive 乘积空间映射到自身，因此
元素数为 `(d^2) * (d^2) = d^4`。这不是 TTNO 表示的一般性质，而是“一个 leaf
合并两个 primitive modes”的 grouping 选择。primitive contraction 恢复
one-mode leaf 后，operator 张量回到 `(O, d, d)`，渐近元素数为 `d^2`。

## 切换点的全模型影响

16 个 modes 时：

- paired：8 个 phonon leaves，`n_active_nodes = 16`；
- contracted：16 个 phonon leaves，`n_active_nodes = 32`。

leaf 个数翻倍，同时每个 leaf 的稠密成本从 d^4 降到 d^2。两个效应叠加，
全模型 wall time 在切换点出现非单调跳变：

- `state_bond` panel（固定 d=10）：M_s=8（contracted）→ M_s=16（paired）时，
  `sop_no_env` 从约 32.5 s 降到约 8.0 s；
- `primitive_basis` panel（固定 M_s=20）：d=16（paired）→ d=32（contracted）时，
  `sop_no_env` 从约 8.4 s 跳到约 35.5 s。

TTNO 路径同样受 active-node 数影响，但绝对幅度小得多。

## 正文与 SI 的分工

- 正文三 panel 图：`modes` 保留 `N_b^3/N_b^2/N_b` 参考线；`state_bond` 与
  `primitive_basis` 只作参数稳健性检查（不报指数、不画幂次参考线），并标注
  切换线。
- SI 图：保留全部 panel 的 largest-four fits 与幂次参考线（M_s^4、常数），
  供审稿人复核；这些是有效 wall-time 指数，不是渐近 FLOP 指数。

## 正确解读

- 大 d 区间的“近常数”是“切换到 contracted layout 之后、固定 body-tree
  工作占主导”的结果，不是 leaf 计算本身 O(1)；isolated leaf 的 FLOPs
  和 TTNO storage 仍渐近 d^2。
- 系统大小 scaling 的唯一主结论来自 `modes` panel（固定 M_s=20、d=10、
  全 paired）：`N_b^3 / N_b^2 / N_b`（`sop_no_env` / `sop_mctdh_like_state_env` /
  `ttno_with_env`）。
- 图件中两个参数 panel 必须标注切换线，并在正文用一句话说明跳变来自
  拓扑切换，而不是数值错误或算法复杂度变化。
