# SOP Debugging Lab

`notebooks/sop_debugging_lab.ipynb` 是一个可执行的十步学习实验。它用固定的小型
Li.W.2024 spin--boson case，把 symbolic `Op`、flat SOP、strict state environment
和 TTNO environment 的实际对象连到同一个可复核的 benchmark workflow。

## 启动与断点

从仓库根目录启动：

```bash
conda run -n reno-3.9 jupyter lab notebooks/sop_debugging_lab.ipynb
```

默认保持 `RUN_BREAKPOINTS=False`，这样可从头到尾不间断地执行 notebook。只有在
某个 investigation 明确标出的 production cell 已经需要调试时，才设为 `RUN_BREAKPOINTS=True`；不要把
它作为普通运行模式。

## 十项调查路线

1. 从 symbolic Hamiltonian 到 snapshot、fit 和 figure 的完整实验路线。
2. 一个 `Op` 如何成为带系数和 node-local factors 的 `SOPTerm`。
3. product term 如何按 `BasisTree.dof2idx` 分配到 tree node。
4. `BasisSet.op_mat()` 如何把 symbolic local operator 变成数值矩阵。
5. 无 environment 的 flat SOP term application 重复了哪些 tree work。
6. strict MCTDH-like SOP 如何以 `(source_node_idx, target_node_idx, term_index)`
   缓存有向边 state messages。
7. strict term cache 与 operator-signature cache 的差异。
8. TTNO operator bonds 和 `TTNEnviron` 如何保存并复用 operator structure。
9. 三条 formal path 的数值一致性与 timing identity。
10. 一个 immutable formal manifest task 如何写入 atomic snapshot、汇总、拟合并绘图。

## 测量对象与算法边界

不要把下列三个对象混为一谈：

- Full-state SOP apply：`SOPBaselineOperator.apply_to_ttns_no_env()` 对完整 state
  构造 flat-SOP 的 `H|psi>`；它不是本 notebook 的 formal timing object。
- All-node local actions：formal benchmark 的唯一 quantity 是
  `local_effective_1site_apply_all_nodes`，即对每个 active tree node 收集 one-site
  local effective-Hamiltonian action。
- Full TDVP propagation：一次完整传播还包括 time-step evolution 的其他工作；它不是
  all-node local-action collection，也没有在此 formal comparison 中计时。

formal comparison 只包含以下三个精确 method labels：

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

`sop_env_plus_operator_cache` 是 optimized、explanatory、non-strict 的
operator-signature reuse path。它可以跨 SOP terms 复用 branch operator structure，
因此不属于 strict MCTDH-like flat-SOP baseline，也被排除在 formal three-method
comparison 之外。

## 已完成结果的正确表述

这些结论都属于 `local_effective_1site_apply_all_nodes` 的 completed formal workflow，
不能替换为 full TDVP propagation 或 full-state `H|psi>` 的结论。

1. Mode-count largest-four-point tail exponents 分别为 `3.109`
   (`sop_no_env`)、`2.035` (`sop_mctdh_like_state_env`) 和 `0.916`
   (`ttno_with_env`)；它们对应 flat traversal、strict per-term state reuse 和
   TTNO operator-plus-state reuse 的差异。
2. Full-workflow state-bond tail exponents 分别约为 `2.180`、`2.243` 和 `2.223`。
   它们是有限窗口的 wall-time effective exponents；isolated full-rank internal
   contraction 的数学成本仍是 `M_s^4` FLOPs。
3. Adaptive primitive contraction 后，large-`d` formal timings 近似常数。这个
   whole-workflow observation 不表示 leaf contraction 为 `O(1)`：isolated paired
   和 primitive-contracted leaves 分别暴露 `d^4` 与 `d^2` 的数学/storage behavior。

## 相关文件与验证

- `benchmarks/sop_debugging_lab.py`：notebook 使用的稳定、print-friendly inspection
  helpers。
- `renormalizer/tn/tests/test_sop_debugging_lab.py`：helper、notebook structure 和
  breakpoint-disabled execution contract。

学习材料的回归检查：

```bash
conda run -n reno-3.9 python -m pytest \
  renormalizer/tn/tests/test_sop_debugging_lab.py \
  renormalizer/tn/tests/test_sop_baseline.py \
  renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py \
  renormalizer/tn/tests/test_li2024_formal_benchmark.py -q
```
