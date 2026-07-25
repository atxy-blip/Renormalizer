# 文档缺口

当前已初始化与 SOP/TTNO environment 任务直接相关的 llmdoc。

后续建议补充：

- 如果后续修改 TDVP sweep 或 local effective Hamiltonian API，补充调用链图。
- 解释 Li.W.2024 full workflow 在 largest-four `M_s` window 中三种方法均约
  `M_s^2.2`，而 isolated full-rank internal-node optimized FLOPs 精确为 `M_s^4`。
  已确认有限尺寸 kernel wall time 会向 4 上升；剩余闭合条件是扩大 full-rank
  full-workflow 区间，并同时报告 throughput、internal/body/leaf 时间占比。
- 量化当前 `local_effective_1site_apply_all_nodes` 与完整 TDVP-VMF evolution step
  的时间组成。闭合条件：相同模型、tree/state 参数下增加 full-step benchmark，或
  明确声明只比较 contraction kernel。
- legacy Hubbard-junction formal array 仍只有 204/216 个快照。闭合条件：明确
  标记为 superseded partial archive，或补齐 no-env `N=300` 和全部 `M_s=300`
  repeats；不要与 189/189 Li.W.2024 spin-boson final result 混用。

已补充：

- `llmdoc/architecture/ttns-ttno-environment.md` 已记录 `SOPOneSiteEffective`、`SOPMCTDHSweepEnvironment`、cache key 与 root/all-nodes timing object 区别。
- `llmdoc/guides/sop-environment-benchmark-flow.md` 已记录四类 benchmark label 和 strict MCTDH-like all-nodes sanity 结果。
- `llmdoc/architecture/primitive-contraction-scaling.md` 已用 actual tensor shape、
  exact optimized FLOPs、TTNO element count 和 peak memory 解释 paired leaf
  `d^4`；primitive contraction 恢复 one-mode leaf 的渐近 `d^2` storage/FLOPs。
- `llmdoc/overview/scaling-benchmark-status.md` 已记录 144/144 diagnostics 和
  189/189 Li.W.2024 rerun 的当前结果。
