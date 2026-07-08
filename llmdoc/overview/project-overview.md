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

- `benchmarks/benchmark_sop_vs_ttno.py`
  - 构造 Hubbard junction / shared-structure benchmark。
  - 比较 flat SOP apply 和 TTNO apply。

- `renormalizer/tn/tests/test_sop_baseline*.py`
  - 验证 SOP dense / apply / expectation 与 TTNO 或 MPO 一致。

- `docs/sop_baseline_code_audit.md`
  - 记录当时的 SOP baseline 审计结论。

## 当前需要补足的点

上一个 commit 的 SOP baseline 可以作为 `sop_no_env`，但还不能代表 “SOP with contraction environment”。

下一阶段要补足：

- 明确 benchmark method 字段：`sop_no_env`, `sop_with_env`, `ttno_with_env`。
- 为 SOP 增加 local effective Hamiltonian / active node 级别的 environment 复用。
- benchmark 分离 environment build time 和 local apply time。
- 用数值一致性证明三条路径对应同一个 Hamiltonian action。
