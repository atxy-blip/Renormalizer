# 项目概览

本仓库是 Renormalizer 的一个工作分支，关注 TTNS/TTNO 与 SOP operator baseline 的对比。

## 上一个 commit 新增内容

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

## 当前需要补足的点

上一个 commit 的 SOP baseline 可以作为 `sop_no_env`，但还不能代表 “SOP with contraction environment”。

下一阶段要补足：

- 明确 benchmark method 字段：`sop_no_env`, `sop_mctdh_like_state_env`, `sop_env_plus_operator_cache`, `ttno_with_env`。
- 为 SOP 增加 local effective Hamiltonian / active node 级别的 environment 复用。
- benchmark 分离 environment build time 和 local apply time。
- 用数值一致性证明四条路径对应同一个 Hamiltonian action。

当前工作区已新增 strict MCTDH-like all-nodes benchmark path：

- `benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment`
- `active_scope=all_nodes`
- cache key: `(source_node_idx, target_node_idx, term_index)`
- 不跨 SOP terms 共享 operator structure。

当前还新增 Ren-style formal Tree benchmark infrastructure：

- `benchmarks/ren_formal_manifest.py`：定义 `N_site/M_s/d` 三个 panel 的 216 个任务。
- `benchmarks/run_ren_formal_point.py`：每个方法、点、repeat 独立运行并原子写 NPZ。
- `benchmarks/scripts/curie_cpu_ren_formal_array.sbatch`：Curie CPU array wrapper。
- `benchmarks/plot_operator_env_scaling.py`：只输出三方法、三 panel PDF。

当前 formal 数据为 204/216 个快照。N panel 支持 strict all-node 的
`N^3/N^2/N`；大 `M_s` 区间三种方法均约 `M_s^3`，大 `d` 区间 SOP 近常数而
TTNO 约 `d^4`。后两项与 Ren.J.2022 中不同程序/算法对象的 `M_s^4` 和 `d^2`
不能直接等同，已作为待诊断问题保留。
