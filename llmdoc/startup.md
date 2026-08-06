# 启动清单

接手本仓库任务时，先按顺序阅读：

1. `llmdoc/index.md`
2. `llmdoc/must/project-basics.md`
3. `llmdoc/must/testing-environment.md`
4. `llmdoc/must/ttns-sop-task-context.md`
5. 与任务直接相关的 architecture / guides 文档

## 当前最重要约定

- 在 Curie 本机测试时使用 conda 环境 `reno-3.9`。
- 推荐命令形态：

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_baseline.py -q
```

- 不使用裸 `python`；当前环境中裸 `python` 不在 PATH。
- 小脚本可用 `python3` 做只读调查，但项目测试和 benchmark 以 `conda run -n reno-3.9 python ...` 为准。

## 当前任务焦点

本分支的核心问题不是简单证明 TTNO 比 SOP 快，而是区分效率来源：

1. `sop_no_env`：flat SOP term-by-term，不构造 contraction environment。
2. `sop_mctdh_like_state_env`：strict MCTDH-like SOP baseline，按 SOP term 构造 sweep-level directed-edge state environment，不共享 operator structure。
3. `sop_env_plus_operator_cache`：优化版 SOP baseline，额外使用 branch/operator signature cache。
4. `ttno_with_env`：TTNO 压缩 operator structure，并使用 TTN contraction environment。

scaling 解释必须区分 timing object：

- `active_scope=root`：root one-site kernel，no-env 预期约 `N^2`。
- `active_scope=all_nodes`：sweep-like all-node local actions，no-env 预期约 `N^3`，strict MCTDH-like state env 预期约 `N^2`。

继续实现前，应先读：

- `llmdoc/architecture/op-to-contraction.md`
- `llmdoc/architecture/ttns-ttno-environment.md`
- `llmdoc/guides/sop-environment-benchmark-flow.md`

继续分析或提交 scaling benchmark 前，还应读：

- `llmdoc/overview/scaling-benchmark-status.md`
- `llmdoc/architecture/primitive-contraction-scaling.md`
- `llmdoc/architecture/paired-vs-contracted-leaves.md`
