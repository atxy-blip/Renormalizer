# 项目概览

本仓库是 Renormalizer 的一个工作分支，关注 TTNS/TTNO 与 SOP operator baseline 的对比。

## Flat SOP baseline

commit `5fbf5a1 Update SOP operator` 新增或修改：

- `renormalizer/tn/sop_baseline.py`
  - 新增 `SOPTerm` 和 `SOPBaselineOperator`。
  - 将 symbolic `Op` term list 作为 flat SOP 表示。
  - 当前 apply 路径逐 product term 直接作用到 TTNS physical axes。

- `renormalizer/tn/__init__.py`
  - 导出 `SOPBaselineOperator` 和 `SOPTerm`。

- `benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`
  - 构造 Hubbard junction / shared-structure benchmark。
  - 比较 flat SOP apply 和 TTNO apply。

- `renormalizer/tn/tests/test_sop_baseline*.py`
  - 验证 SOP dense / apply / expectation 与 TTNO 或 MPO 一致。

- `docs/sop_baseline_code_audit.md`
  - 记录当时的 SOP baseline 审计结论。

## Strict all-node operator benchmark

分支已实现 strict MCTDH-like all-nodes benchmark path：

- `benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment`
- `active_scope=all_nodes`
- cache key: `(source_node_idx, target_node_idx, term_index)`
- 不跨 SOP terms 共享 operator structure。

正式比较使用：

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

`sop_env_plus_operator_cache` 保留为包含 operator-signature reuse 的中间路径，
不代表 strict flat-SOP baseline。

## Formal benchmark infrastructure

commit `7c974c0` 新增 Ren-style formal Tree benchmark infrastructure：

- `benchmarks/ren_formal_manifest.py`：定义 `N_site/M_s/d` 三个 panel 的 216 个任务。
- `benchmarks/run_ren_formal_point.py`：每个方法、点、repeat 独立运行并原子写 NPZ。
- `benchmarks/scripts/curie_cpu_ren_formal_array.sbatch`：Curie CPU array wrapper。
- `benchmarks/plot_operator_env_scaling.py`：只输出三方法、三 panel PDF。

该 legacy formal 数据为 204/216 个快照。N panel 支持 strict all-node 的
`N^3/N^2/N`；大 `M_s` 区间三种方法均约 `M_s^3`，大 `d` 区间 SOP 近常数而
TTNO 约 `d^4`。该数据集保留为 partial historical source。

## 当前完成状态

后续工作已完成两组正式实验：

- contraction diagnostics：144/144 tasks，隔离 FLOPs、dense-kernel timing、
  tensor storage 和 peak memory；
- Li.W.2024 spin-boson rerun：189/189 tasks，正式比较三条 operator path。

诊断确认 full-rank binary internal-node contraction 是 `M_s^4` optimized FLOPs；
旧 `d^4` 来自 paired two-mode leaf 的四个 physical operator axes。启用 primitive
contraction 后，one-mode leaf 的 TTNO storage 和 isolated contraction 渐近 `d^2`。

当前结果和待办见：

- `llmdoc/overview/scaling-benchmark-status.md`
- `llmdoc/architecture/primitive-contraction-scaling.md`
