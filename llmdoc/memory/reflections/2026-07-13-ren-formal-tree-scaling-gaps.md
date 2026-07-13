# Reflection: Ren-style formal Tree scaling 与未解差异

## 本轮目标和算法身份

当前正式实验借用 Ren.J.2022 Figure 10 的三个控制变量和参数范围，但测试对象仍是
Renormalizer 的 Tree tensor network，不是一维 MPS TD-DMRG，也不是 Heidelberg
ML-MCTDH 程序的完整 propagation step。

正式图只比较：

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

其中 strict SOP path 由
`benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment` 实现。它保留
逐项 SOP，用 `(source_node_idx, target_node_idx, term_index)` 缓存有向边 message，
不做跨 term operator grouping。`sop_env_plus_operator_cache` 只是中间实现，不进入
正式图。

## 正式实验参数和进度

`benchmarks/ren_formal_manifest.py` 定义 216 个独立任务，每个点、方法各 3 次重复：

```text
N_site panel: M_s=20, d=10, N_total_sites=18,30,46,74,118,186,300
M_s panel:    N_phonon=16, d=10, M_s=10,20,30,50,70,100,150,220,300
d panel:      N_phonon=16, M_s=20, d=5,10,20,30,40,50,70,100
```

job 114789 因直接运行文件导致 package import 失败。修正为
`python -m benchmarks.run_ren_formal_point` 后提交 replacement array 115005。
每个任务原子写 JSON-backed compressed NPZ，避免长作业结束前没有结果。

截至 2026-07-13 的可复核状态：

```text
snapshots: 204 / 216, all available rows status=ok
frozen raw: benchmarks/results/operator_env_scaling/ren_formal/partial_20260713_raw.csv
partial PDF: benchmarks/results/operator_env_scaling/final/ren_formal_partial_20260713_scaling_three_panel.pdf
missing: N=300 的 sop_no_env 3 repeats；M_s=300 的三个方法共 9 repeats
max relative_error_vs_ttno: about 2.03e-15
```

因此当前结果必须称为 partial formal result，不能把缺失端点外推成最终拟合。

## 当前观测

### Site number

对 `N_total_sites` 的 all-points fit：

```text
sop_no_env                  alpha ~= 3.258  (N=18...186)
sop_mctdh_like_state_env    alpha ~= 2.156  (N=18...300)
ttno_with_env               alpha ~= 1.052  (N=18...300)
```

strict SOP 最后区间 `N=186 -> 300` 的 local slope 约 2.03。这个 panel 支持当前
all-node timing object 的 `N^3/N^2/N` 预期，但 no-env 缺失 `N=300`。

### State bond dimension

现有完整端点到 `M_s=220`。全区间 fit 被小 `M_s` 固定开销压低；只看大尺寸：

```text
M_s >= 50:
  sop_no_env                  alpha ~= 2.82
  sop_mctdh_like_state_env    alpha ~= 2.87
  ttno_with_env               alpha ~= 3.12

M_s >= 70:
  sop_no_env                  alpha ~= 2.91
  sop_mctdh_like_state_env    alpha ~= 2.92
  ttno_with_env               alpha ~= 3.11
```

当前 Tree kernel 的三条路径都趋近 `M_s^3`。图中的三条虚线因此统一画
`propto M_s^3`，但这是当前观测的参考线，不是对 Ren.J.2022 的理论修正。

### Primitive basis dimension

`d=5...100` 已完成。大 `d` 区间：

```text
d >= 30:
  sop_no_env                  alpha ~= 0.26
  sop_mctdh_like_state_env    alpha ~= 0.19
  ttno_with_env               alpha ~= 4.05
```

strict SOP 在 `d=5...100` 近似常数，但仍从约 3.28 s 增至 4.18 s。TTNO 的
environment build 和 apply 都快速增长；`d=100` 时约为 21.49 s 和 29.82 s，
不是 TTNO construction 被计时造成的假象。正式图暂画 SOP 常数和 TTNO
`propto d^4` 参考线，线段只覆盖后半数据并与最后一点重合。

## 为什么不能直接复现 Ren.J.2022

Ren.J.2022 Figure 10 测的是 spin-boson 模型的一次 TDVP-VMF evolution step，
并比较当时 Heidelberg ML-MCTDH 与一维 MPS TD-DMRG 实现。当前实验测的是
Hubbard molecular-junction Tree 上所有 node 的 one-site local effective action
集合，使用随机 TTNS，没有时间积分器、SPF 方程、regularization 或完整 propagation。

因此当前工作只借鉴它的参数扫描流程：

```text
(a) M_s=20, d=10, number of modes varies
(b) number of modes=16, d=10, M_s varies
(c) number of modes=16, M_s=20, d varies
```

不能把 `ttno_with_env` 直接标成论文的 TD-DMRG，也不能把
`sop_mctdh_like_state_env` 标成 Heidelberg ML-MCTDH wall time。N panel 的一致只说明
当前 kernel 的 operator/state reuse 结构符合预期，不证明两个程序完全等价。

## 重点未解问题

### 1. 为什么 strict Tree SOP 是 M_s^3，而不是 binary ML-MCTDH 的 M_s^4

当前三种 operator 表示共用 Renormalizer TTNS tensor、tree topology 和局域
contraction primitive。operator 表示主要改变 N scaling 和 prefactor，不一定改变
主导 state contraction 的 `M_s` 次数。观测到 `M_s^3` 可能说明当前 contraction
实质上是 matrix-like，或 quantum-number block/tree tensor shape 使一个理论上随
`M_s` 增长的指标没有等比例增长。

但这还不是结论。尚未记录每个 node 的实际 tensor shape、非零 block、平均 bond、
`opt_einsum` contraction path 和 FLOP estimate；`M_s=300` 也缺失。必须先量化这些
因素，再判断是 pre-asymptotic、QN sparsity、tree layout，还是 timing object 不同。

### 2. 为什么 Tree TTNO 是 d^4，而不是论文 TD-DMRG 的 d^2

论文的 `d^2` 属于 MPS TD-DMRG physical-index contraction；当前是 binary TTNS/TTNO
局域 effective action，算法身份不同。当前 `BasisSHO` 的 `x/x^2/p^2` 是 dense local
matrix，也没有 Heidelberg ML-MCTDH bottom-layer DVR 的 `O(d)` 优化。

仍需解释为什么当前 dense Tree contraction 达到约 `d^4`，而不只是 `d^2`。需要审计
`TTNEnviron` 和 `hop_expr1` 在 physical leaf 上生成的 expression，记录最大中间张量、
实际 FLOP 和 contraction path 随 d 的增长。env build 与 apply 都呈高次增长，说明
问题不能归因于单一阶段。

## 下一步闭环

1. 完成或重跑缺失的 12 个任务，先形成 216/216 final aggregate。
2. 在每个 panel 输出 actual bond dimensions、node tensor shapes、QN block 数和元素数。
3. 从 `opt_einsum` expression 记录 optimized FLOP、largest intermediate 和 path。
4. 对 `M_s` 增加无 QN 或可控 full-rank uniform binary tree 对照，判断 nominal bond 与
   actual contraction dimension 是否一致。
5. 对 `d` 单独拆分 TTNO environment build、expression build、apply，并审计 physical
   leaf expression；必要时增加 dense-vs-DVR/local-operator 对照。
6. 增加完整 TDVP-VMF step timing，明确 local all-node kernel 与 propagation wall time
   的差额；若要声称复现 Heidelberg，必须另做相同模型、树、积分设置的直接比较。

在这些诊断完成前，最严谨的表述是：当前 Tree benchmark 已复现 N 方向的
`N^3/N^2/N`，但 `M_s` 和 `d` 方向反映的是 Renormalizer Tree contraction kernel，
与 Ren.J.2022 中 Heidelberg ML-MCTDH / MPS TD-DMRG 的指数差异仍是待解释问题。
