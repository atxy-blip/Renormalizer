# 文档缺口

当前已初始化与 SOP/TTNO environment 任务直接相关的 llmdoc。

仍待处理：

- 如果后续修改 TDVP sweep 或 local effective Hamiltonian API，补充调用链图。
- legacy Hubbard-junction formal array 仍只有 204/216 个快照。闭合条件：明确
  标记为 superseded partial archive，或补齐 no-env `N=300` 和全部 `M_s=300`
  repeats；不要与 189/189 Li.W.2024 spin-boson final result 混用。

已决定/已闭合（2026-08-06）：

- 不做完整 TDVP/传播 step benchmark。`local_effective_1site_apply_all_nodes`
  与完整 step 的时间组成差异是刻意边界，不是缺口。
- 不扩大 full-rank full-workflow 区间，不做 M_s 时间占比/throughput 分解。
- Li.W.2024 的 M_s/d 指数与幂次参考线保留在 SI；正文只报 modes panel 指数。
  isolated full-rank internal-node `M_s^4` FLOP 结论保留在 contraction
  diagnostics，SI 中的 M_s^4 参考线是有效 wall-time 参考，不是 FLOP 渐近指数。
- paired vs contracted topology switch 已由
  `llmdoc/architecture/paired-vs-contracted-leaves.md` 专门说明。

已补充：

- `llmdoc/architecture/ttns-ttno-environment.md` 已记录 `SOPOneSiteEffective`、`SOPMCTDHSweepEnvironment`、cache key 与 root/all-nodes timing object 区别。
- `llmdoc/guides/sop-environment-benchmark-flow.md` 已记录四类 benchmark label 和 strict MCTDH-like all-nodes sanity 结果。
- `llmdoc/architecture/primitive-contraction-scaling.md` 已用 actual tensor shape、
  exact optimized FLOPs、TTNO element count 和 peak memory 解释 paired leaf
  `d^4`；primitive contraction 恢复 one-mode leaf 的渐近 `d^2` storage/FLOPs。
- `llmdoc/overview/scaling-benchmark-status.md` 已记录 144/144 diagnostics、
  189/189 Li.W.2024 rerun、正文/SI 分工和 2026-08-06 正式解释口径。
- `llmdoc/architecture/paired-vs-contracted-leaves.md` 已说明两种叶子布局与
  拓扑切换跳变。
