# Reflection: operator scaling result archive

## 背景

adaptive operator benchmark 的结果目录曾同时包含 root-only、all-nodes
开发过程、strict baseline、operator-cache 中间路径和更早的 full-state
SOP-vs-TTNO 实验。文件名主要按 profile 和 Slurm job id 组织，容易把
`large_114126` 这种规模更大但 timing object 不同的结果误认为最终结论。

## 关键教训

benchmark 结果应优先按算法身份和 timing object 归档，而不是只按
`sanity/medium/large` 或 job id 排列。最终发布目录只保留一个明确的数据源、
汇总、拟合和图；历史结果通过 manifest 说明为什么不能用于当前结论。

归档旧脚本前还必须检查代码依赖。旧
`benchmark_sop_vs_ttno.build_hubbard_junction_case()` 和当前 adaptive
benchmark builder 同名，但前者返回 current operator terms，后者没有。
直接替换测试导入会导致返回值契约错误。正确处理是让历史 full-state
等价性测试显式导入归档 builder，避免把两个不同 API 强行合并。

## 当前发布口径

最终 PDF 使用 Slurm job 114336：

```text
active_scope = all_nodes
scaling_path = lead_only
N_total_sites = 18, 34, 66
```

主图只显示三条理论 baseline：

```text
sop_no_env                  fitted alpha = 3.246
sop_mctdh_like_state_env    fitted alpha = 2.167
ttno_with_env               fitted alpha = 1.063
```

图中同时给出 `alpha=3,2,1` 的理论虚线。`sop_env_plus_operator_cache`
保留在 raw CSV 中用于追溯，但不进入主图。

