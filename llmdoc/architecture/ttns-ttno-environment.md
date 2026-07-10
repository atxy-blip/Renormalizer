# TTNS/TTNO Environment 审计

## 现有 TTNO environment

核心类：`renormalizer/tn/tree.py::TTNEnviron`

`TTNEnviron` 是一棵与 TTNS/TTNO 拓扑相同的 environment tree。每个 `TreeNodeEnviron` 保存：

- `environ_parent`：来自 parent 方向的 contraction boundary。
- `environ_children`：来自每个 child branch 的 contraction boundary。

构造分两轮：

```text
TTNEnviron(ttns, ttno)
  -> build_children_environ(ttns, ttno)
  -> build_parent_environ(ttns, ttno)
```

其中：

- `build_children_environ_node()` 从 child/subtree 方向向 parent 构造 environment。
- `build_parent_environ_node()` 从 parent 和 sibling branches 方向向某个 child 构造 environment。

每个 environment tensor 的三个虚拟方向对应：

```text
bra bond, ttno operator bond, ket bond
```

## Local effective Hamiltonian

核心文件：`renormalizer/tn/hop_expr.py`

- `hop_expr1()`：one-site effective Hamiltonian。
- `hop_expr2()`：two-site effective Hamiltonian。
- `hop_expr0()`：TDVP projector splitting 中 zero-site backward evolution。

`hop_expr1()` 对 active node 做的事：

1. 取 active node 每个 child branch 的 `environ_children`。
2. 取 active node parent 方向的 `environ_parent`。
3. 加入 active node 的 TTNO tensor。
4. 生成一个 `opt_einsum` expression，输入是 active TTNS tensor，输出是局域 Hamiltonian action。

这正是本任务中说的 contraction environment。

## TDVP / ground-state 调用链

TDVP：

```text
TTNS.evolve(ttno, tau)
  -> renormalizer/tn/time_evolution.py
  -> evolve_tdvp_ps / evolve_tdvp_ps2 / evolve_tdvp_vmf
  -> TTNEnviron(ttns, ttno)
  -> hop_expr1 / hop_expr2
```

Ground-state optimization：

```text
optimize_ttns(ttns, ttno)
  -> TTNEnviron(ttns, ttno)
  -> optimize_2site()
  -> hop_expr2()
```

## TTNO.apply 不是 environment path

`TTNO.apply(ttns)` 逐 node contraction：

```text
for snode, new_snode, onode in zip(ttns, new, ttno):
    contract snode.tensor with onode.tensor
    merge state bond and operator bond dimensions
```

它利用 TTNO operator bond 的压缩结构，但没有构造 `TTNEnviron`，也不是 active-node local effective Hamiltonian。

## 当前 SOP baseline 的状态

`SOPBaselineOperator.apply_to_ttns()` 当前默认 dispatch 到 `apply_to_ttns_no_env()`，后者逐 term 调 `_apply_term_to_ttns()`：

- 每个 product term 独立遍历整棵 TTNS。
- 仅缓存 `(node_idx, op.to_tuple()) -> local matrix factors`。
- 不构造 branch environment。
- 不跨 product terms 复用 state-tree contraction boundary。

因此它应归类为 `sop_no_env`。

full-state `method="sop_with_env"` 当前仍未实现，并应明确抛出 `NotImplementedError`。

benchmark 里有三类 SOP local effective Hamiltonian paths。

### One-site branch cache

`SOPOneSiteEffective` 是 one-site local effective Hamiltonian action 的基础实现，位置：

```text
benchmarks/benchmark_adaptive_operator_env.py::SOPOneSiteEffective
```

复用粒度：

- active node 的每个 child branch；
- branch root index；
- branch subtree 上非 identity local `Op` 的 signature；
- 相同 branch signature 的 SOP terms 共享同一个 precontracted branch environment。

这种 path 对应 `sop_env_plus_operator_cache`。它包含 operator-structure reuse，不能作为 strict Heidelberg/MCTDH-like SOP baseline。

`SOPOneSiteEffective` 也支持 term-index cache：

```text
(branch_root_idx, term_index)
```

这个模式不跨 SOP terms 共享 operator signature，但如果对每个 active node 单独构造，仍然会重复 building state environment，不是 sweep-level MCTDH-like reuse。

### Strict MCTDH-like sweep environment

strict MCTDH-like baseline 位置：

```text
benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment
```

它对每个 SOP term 和每条 tree edge 构造两个方向的 state environment message：

```text
child -> parent
parent -> child
```

cache key 是：

```text
(source_node_idx, target_node_idx, term_index)
```

这表示：

- 保留 flat SOP term list；
- 不使用 TTNO/MPO operator bonds；
- 不跨 product terms 合并相同 operator subtree；
- 只复用 state-tree / mean-field-like contraction boundary。

all-nodes sweep 下，cache entry 数应为：

```text
n_sop_terms * 2 * (n_nodes - 1)
```

这对应 `sop_mctdh_like_state_env`。复杂度预期是：

```text
env build + all-node local action ~ n_sop_terms * n_nodes ~ N^2
```

### Timing object matters

`active_scope=root` 只测 root one-site action。此时 naive no-env 是：

```text
n_sop_terms * n_tree ~ N^2
```

`active_scope=all_nodes` 测所有 active nodes 的 one-site action。此时 naive no-env 是：

```text
n_active_nodes * n_sop_terms * n_tree ~ N^3
```

因此不能用 root-only benchmark 解释 Heidelberg MCTDH propagation / full sweep scaling。

## 可复用但不能直接照搬的部分

可复用：

- `TTNEnviron` 的 branch environment 概念。
- `get_child_indices()` / `get_parent_indices()` 的 index 设计思路。
- `hop_expr1/2` 的 local effective Hamiltonian API 形态。

不能直接照搬：

- `TTNEnviron` 当前假设 operator 是一个 TTNO tensor network，environment tensor 有 operator bond 维度。
- flat SOP 没有 TTNO bond。strict MCTDH-like SOP-with-env 需要按 product term 和 directed tree edge 缓存 state environment；优化版 SOP 才可以额外按 branch operator signature 合并。
