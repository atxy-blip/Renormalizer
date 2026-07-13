# Reflection: strict MCTDH-like SOP baseline

## 背景

本轮任务调查 `SOP with env` scaling 为什么低于理论预期，并进一步实现 strict MCTDH-like SOP baseline。

导师预期的三条渐近关系是：

```text
SOP no env       ~ N^3
SOP with env     ~ N^2
TTNO with env    ~ N
```

前期 benchmark 得到：

```text
SOP no env       slope ~= 2
SOP with env     slope ~= 1.36
TTNO with env    slope ~= 1
```

## 关键教训

旧 benchmark 的核心问题不是数值 contraction 错，而是 timing object 和 baseline identity 错。

`HEAD` 版本只测 root one-site local effective Hamiltonian action。对这个对象：

```text
T_no_env(root) ~ n_sop_terms * n_tree ~ N^2
```

因此 root-only `sop_no_env` 不应期待 `N^3`。导师预期的 `N^3` 对应 all-nodes sweep / propagation-like kernel：

```text
T_no_env(all_nodes) ~ n_active_nodes * n_sop_terms * n_tree ~ N^3
```

另一个中间错误是：即使加入 `active_scope=all_nodes`，如果 `sop_mctdh_like_state_env` 仍然对每个 active node 调一次 one-site builder，就会重复构造 environment：

```text
for active_node:
    build per-term branch env for this active_node
```

这仍是 `N^3`，不是 MCTDH-like sweep-level reuse。

## 当前正确实现

当前 strict MCTDH-like baseline 在 `benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment`。

它对每个 SOP term 和每条 tree edge 构造双向 directed-edge message：

```text
child -> parent
parent -> child
```

cache key 是：

```text
(source_node_idx, target_node_idx, term_index)
```

这个 key 保留 `term_index`，不使用 operator subtree signature，因此不跨 SOP terms 合并相同 operator structure。它只复用 state-tree / mean-field-like contraction environment，符合 strict MCTDH-like SOP baseline。

all-nodes 下 cache entry 数应满足：

```text
n_env_cache_entries = n_sop_terms * 2 * (n_nodes - 1)
```

测试 `test_strict_mctdh_state_env_reuses_term_messages_across_active_nodes` 固定了这个性质。

## 结果口径

四点 all-nodes sanity (`n_lead=1,2,4,8`) 显示：

```text
fit vs n_lead, large-only:
  sop_no_env                  ~= 3.02
  sop_mctdh_like_state_env    ~= 2.03
  sop_env_plus_operator_cache ~= 2.43
  ttno_with_env               ~= 1.01
```

这支持理论关系：

```text
SOP no env       ~ N^3
strict SOP env   ~ N^2
TTNO with env    ~ N
```

`sop_env_plus_operator_cache` 目前仍是 per-active-node signature-cache path，不是完整 sweep-level operator-cache baseline。

## 后续注意

- 报告 scaling 时必须说明 `active_scope=root` 还是 `active_scope=all_nodes`。
- root-only benchmark 不能用来验证 no-env `N^3`。
- `sop_mctdh_like_state_env` 必须走 sweep-level directed-edge message cache；否则只是 per-active-node state env rebuild。
- `sop_env_plus_operator_cache` 与 strict MCTDH baseline 不同，不能代表 Heidelberg MCTDH-like SOP baseline。
