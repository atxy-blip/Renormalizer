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
- 当前 `SOPBaselineOperator.apply_to_ttns()` 没有 contraction environment，只做 local matrix cache。
- 因此当前 benchmark 只覆盖 flat SOP vs TTNO apply，还没有覆盖 fair `sop_with_env`。
