# 文档缺口

当前已初始化与 SOP/TTNO environment 任务直接相关的 llmdoc。

后续建议补充：

- 如果后续修改 TDVP sweep 或 local effective Hamiltonian API，补充调用链图。
- 解释 strict Tree SOP / TTNO 在大 `M_s` 区间为何都约为 `M_s^3`，而 Ren.J.2022
  binary ML-MCTDH 报告约 `M_s^4`。闭合条件：记录每个 node 的实际 bond/tensor
  shape、QN block/元素数、opt_einsum FLOP/path，并完成 `M_s=300` 或更大对照。
- 解释 Tree TTNO 在大 `d` 区间为何约为 `d^4`，而论文 MPS TD-DMRG 报告约
  `d^2`。闭合条件：分别审计 `TTNEnviron` 和 `hop_expr1` 的 physical-leaf
  expression、largest intermediate 和 FLOP scaling，并比较 dense local operator
  与 DVR/可利用结构的实现。
- 量化当前 `local_effective_1site_apply_all_nodes` 与完整 TDVP-VMF evolution step
  的时间组成。闭合条件：相同模型、tree/state 参数下增加 full-step benchmark，或
  明确声明只比较 contraction kernel。
- formal array 当前只有 204/216 个快照。闭合条件：补齐缺失的 no-env `N=300`
  和全部 `M_s=300` repeats，生成 final aggregate 和 final PDF。

已补充：

- `llmdoc/architecture/ttns-ttno-environment.md` 已记录 `SOPOneSiteEffective`、`SOPMCTDHSweepEnvironment`、cache key 与 root/all-nodes timing object 区别。
- `llmdoc/guides/sop-environment-benchmark-flow.md` 已记录四类 benchmark label 和 strict MCTDH-like all-nodes sanity 结果。
