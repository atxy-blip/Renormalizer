# TTNS/SOP Environment 任务上下文

老师的问题是：当前 SOP baseline 是否因为没有 contraction environment 而过慢，从而不公平地放大了 flat SOP 的重复缩并开销。

需要清楚区分三条路径：

1. `sop_no_env`
   - 保留 flat SOP term-by-term 逻辑。
   - 不构造 contraction environment。
   - 用来展示 naive product-term traversal 的重复开销。

2. `sop_with_env`
   - Hamiltonian 仍表示为 SOP term list。
   - 对 active node / active subtree 的外部 branch 预构造 environment。
   - 不同 SOP terms 在相同 branch/operator signature 上复用环境。
   - 这是更接近 ML-MCTDH local mean-field / effective Hamiltonian 思路的 baseline。

3. `ttno_with_env`
   - Hamiltonian 先压缩为 TTNO。
   - TTNO bond 共享不同 product terms 的公共 operator structure。
   - TDVP / ground-state local update 使用 `TTNEnviron` 和 `hop_expr1/2`。

当前审计结论：

- `TTNO.apply()` 利用 TTNO operator bond 结构，但不是 `TTNEnviron` 路径。
- TDVP / ground-state local effective Hamiltonian 路径已有 `TTNEnviron`。
- 当前 `SOPBaselineOperator.apply_to_ttns()` 默认走 `sop_no_env`，显式入口是 `apply_to_ttns_no_env()`；它没有 contraction environment，只做 local matrix cache。
- full-state `SOPBaselineOperator.apply_to_ttns(..., method="sop_with_env")` 仍未实现，并应继续抛出 `NotImplementedError`，避免把 no-env 误标成 with-env。
- 当前 adaptive benchmark 已实现 one-site local effective Hamiltonian action 版本的 `sop_with_env`，用 branch signature cache 跨 SOP terms 复用 contraction environment。

当前正式 benchmark 解释口径：

- `lead_only`：固定 `n_phonon=0`，扫描 `n_lead`，用于隔离 fermionic lead mode 增长。
- `balanced_lead_phonon`：同时增加 `n_lead` 和 `n_phonon`，用于更接近 molecular junction 整体变大。
- `n_total_sites = 4 * n_lead + 2 + n_phonon`，是 TTNS/TTNO 物理自由度 site 数。
- `n_sop_terms = 12 * n_lead + 4 * n_phonon`，是 Hamiltonian 的 SOP product term 数，不是 site 数或 basis 维数。
- `alpha` 是 `t(N)=C*N^alpha` 的 log-log wall-time scaling exponent，必须说明横轴是 `n_total_sites` 还是 `n_sop_terms`。
