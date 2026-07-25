# TTNS/SOP Environment 任务上下文

老师的问题是：当前 SOP baseline 是否因为没有 contraction environment 而过慢，从而不公平地放大了 flat SOP 的重复缩并开销。

需要清楚区分四条路径：

1. `sop_no_env`
   - 保留 flat SOP term-by-term 逻辑。
   - 不构造 contraction environment。
   - 用来展示 naive product-term traversal 的重复开销。

2. `sop_mctdh_like_state_env`
   - Hamiltonian 仍表示为 flat SOP term list。
   - 逐 SOP product term 处理，不把多个 terms 压缩为 TTNO/MPO。
   - 对整棵 TTNS tree 构造 per-term directed-edge state environment / mean-field-like message。
   - 不跨 SOP terms 合并相同 operator subtree。
   - 这是 strict MCTDH-like SOP baseline。

3. `sop_env_plus_operator_cache`
   - Hamiltonian 仍表示为 SOP term list。
   - 对 active node / active subtree 的外部 branch 预构造 environment。
   - 不同 SOP terms 在相同 branch/operator signature 上复用环境。
   - 这是优化版 SOP baseline，包含 operator-structure reuse，不能直接代表 Heidelberg MCTDH-like SOP baseline。

4. `ttno_with_env`
   - Hamiltonian 先压缩为 TTNO。
   - TTNO bond 共享不同 product terms 的公共 operator structure。
   - TDVP / ground-state local update 使用 `TTNEnviron` 和 `hop_expr1/2`。

当前审计结论：

- `TTNO.apply()` 利用 TTNO operator bond 结构，但不是 `TTNEnviron` 路径。
- TDVP / ground-state local effective Hamiltonian 路径已有 `TTNEnviron`。
- 当前 `SOPBaselineOperator.apply_to_ttns()` 默认走 `sop_no_env`，显式入口是 `apply_to_ttns_no_env()`；它没有 contraction environment，只做 local matrix cache。
- full-state `SOPBaselineOperator.apply_to_ttns(..., method="sop_with_env")` 仍未实现，并应继续抛出 `NotImplementedError`，避免把 no-env 误标成 with-env。
- 当前 adaptive benchmark 支持 `active_scope=root` 和 `active_scope=all_nodes`。
- `active_scope=root` 只测 root one-site local effective Hamiltonian action。此时 `sop_no_env` 预期是 `n_sop_terms * n_tree ~ N^2`，不能用来验证 no-env `N^3`。
- `active_scope=all_nodes` 测所有 TTNS node 的 one-site local effective action，接近 sweep / propagation kernel 的缩并对象。此时 naive no-env 预期为 `n_active_nodes * n_sop_terms * n_tree ~ N^3`。
- 当前 strict MCTDH-like path 是 `benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment`。它按 `(source_node_idx, target_node_idx, term_index)` 缓存 directed-edge message，不做 operator signature sharing。

当前正式 benchmark 解释口径：

- `lead_only`：固定 `n_phonon=0`，扫描 `n_lead`，用于隔离 fermionic lead mode 增长。
- `balanced_lead_phonon`：同时增加 `n_lead` 和 `n_phonon`，用于更接近 molecular junction 整体变大。
- `n_total_sites = 4 * n_lead + 2 + n_phonon`，是 TTNS/TTNO 物理自由度 site 数。
- `n_sop_terms = 12 * n_lead + 4 * n_phonon`，是 Hamiltonian 的 SOP product term 数，不是 site 数或 basis 维数。
- `alpha` 是 `t(N)=C*N^alpha` 的 log-log wall-time scaling exponent，必须说明横轴是 `n_total_sites` 还是 `n_sop_terms`。
- 报告 `alpha` 时也必须说明 timing object：`quantity=local_effective_1site_apply` 或 `quantity=local_effective_1site_apply_all_nodes`。

当前理论 / 实测口径：

```text
all_nodes, fit vs n_lead, large-only:
  sop_no_env                  ~= 3
  sop_mctdh_like_state_env    ~= 2
  ttno_with_env               ~= 1
```

`sop_env_plus_operator_cache` 目前是 per-active-node branch signature cache path，不是完整 sweep-level operator-cache baseline。

## Legacy 2026-07-13 Hubbard-junction formal benchmark

正式数组固定比较 `sop_no_env`、`sop_mctdh_like_state_env` 和
`ttno_with_env`，每个点 3 repeats。该 legacy 数据集为 204/216 个
`status=ok` 快照，缺少
`N=300` 的 no-env 和 `M_s=300` 的全部方法，仍属于 partial result。

现有数据支持：

```text
N_total_sites:
  sop_no_env                  alpha ~= 3.26  (up to N=186)
  sop_mctdh_like_state_env    alpha ~= 2.16  (up to N=300)
  ttno_with_env               alpha ~= 1.05  (up to N=300)

large M_s window:
  all three methods           alpha ~= 3

large d window:
  SOP methods                 approximately constant
  ttno_with_env               alpha ~= 4
```

`M_s^3` 和 TTNO `d^4` 是当前 Tree kernel 的观测，不是从 Ren.J.2022 继承的
理论结论。论文测试 Heidelberg ML-MCTDH / MPS TD-DMRG 的完整 evolution step；
当前 quantity 是 Hubbard-junction random TTNS 上的
`local_effective_1site_apply_all_nodes`。为什么 strict Tree SOP 没有显示 binary
ML-MCTDH 的 `M_s^4`，以及为什么 Tree TTNO 没有显示论文 TD-DMRG 的 `d^2`，仍需
用实际 tensor shape、QN block、opt_einsum FLOP/path 和 full-step timing 诊断。

该 204/216 数据集现在作为 legacy partial result 保留。后续已改用
Li.W.2024 sub-Ohmic spin-boson model 和 adaptive primitive contraction 做正式重跑。

## 当前诊断结论

144-task contraction diagnostic 已闭合两个 tensor-shape 问题：

```text
full-rank binary internal node:
  optimized FLOPs ~ M_s^4

paired two-mode phonon leaf:
  operator tensor/storage ~ d^4

primitive-contracted one-mode leaf:
  operator tensor/storage ~ d^2
```

因此旧 Hubbard tree 的 `d^4` 来自每个 leaf 合并两个 primitive modes 后产生的
四个 physical operator axes，不是 TTNO 一般性质。旧 `M_s^3` 是有限测试区间的
wall-time exponent；isolated shape-only kernel 的数学 FLOP 次数是 `M_s^4`。

## 当前正式 Li.W.2024 spin-boson rerun

正式 rerun 有 189/189 个 `status=ok` snapshots，比较相同三条 operator path，
每个参数点 3 repeats。测量对象仍是：

```text
quantity = local_effective_1site_apply_all_nodes
```

largest-four-point wall-time fit：

```text
N_b:
  sop_no_env                  3.109
  sop_mctdh_like_state_env    2.035
  ttno_with_env               0.916

M_s:
  sop_no_env                  2.180
  sop_mctdh_like_state_env    2.243
  ttno_with_env               2.223

large d, with primitive contraction when d > M_s:
  all three methods           approximately constant
```

`N_b` panel 支持 `N_b^3/N_b^2/N_b` operator/state reuse 口径。`M_s` panel 的约
2.2 仍是 whole-workflow wall-time 有效指数，不能替代 internal contraction 的
`M_s^4` FLOP 结论。大 `d` whole-workflow 近常数是固定 body-tree work 主导，
isolated leaf 和 TTNO storage 仍渐近 `d^2`。

详情：

- `llmdoc/overview/scaling-benchmark-status.md`
- `llmdoc/architecture/primitive-contraction-scaling.md`
