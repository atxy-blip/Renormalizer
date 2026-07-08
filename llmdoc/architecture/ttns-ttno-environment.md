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

## 当前 SOP baseline 的缺口

`SOPBaselineOperator.apply_to_ttns()` 逐 term 调 `_apply_term_to_ttns()`：

- 每个 product term 独立遍历整棵 TTNS。
- 仅缓存 `(node_idx, op.to_tuple()) -> local matrix factors`。
- 不构造 branch environment。
- 不跨 product terms 复用 state-tree contraction boundary。

因此它应归类为 `sop_no_env`。

## 可复用但不能直接照搬的部分

可复用：

- `TTNEnviron` 的 branch environment 概念。
- `get_child_indices()` / `get_parent_indices()` 的 index 设计思路。
- `hop_expr1/2` 的 local effective Hamiltonian API 形态。

不能直接照搬：

- `TTNEnviron` 当前假设 operator 是一个 TTNO tensor network，environment tensor 有 operator bond 维度。
- flat SOP 没有 TTNO bond。SOP-with-env 需要按 product term 的 branch operator signature 缓存，而不是按 TTNO bond contraction。
