# SOP Environment Benchmark 实现流程

目标是实现并 benchmark 三条路径：

```text
sop_no_env -> sop_with_env -> ttno_with_env
```

不要把物理 bath/lead/phonon environment 与 contraction environment 混淆。

## Step 1：保留并命名 naive SOP

当前 `SOPBaselineOperator.apply_to_ttns()` 是 flat SOP term-by-term apply。

建议：

- 保留现有行为。
- 增加清晰别名或 benchmark method name：`sop_no_env`。
- 文档里说明它没有 branch contraction cache，只缓存 local matrix factor。

这条路径用于展示不构造 environment 的重复 traversal / contraction 开销。

## Step 2：先实现 one-site SOP-with-env

最小可验证版本不必一开始覆盖完整 TDVP sweep。建议先实现 active node 的 local effective Hamiltonian action：

```text
build_sop_one_site_env(psi, sop, active_node)
apply_sop_one_site_env(env, active_tensor)
```

复用粒度建议：

- 对 active node 的每个相邻 branch 独立构造 environment。
- cache key 包含 branch edge 和该 branch 上的 operator signature。
- 如果一个 SOP term 在该 branch 全是 identity，使用 identity branch environment。
- 多个 SOP terms 有相同 branch signature 时复用同一个 environment tensor。

第一版可以只支持 one-site active node。two-site active subtree 可后续扩展。

## Step 3：TTNO-with-env wrapper

现有路径可直接包装：

```python
ttne = TTNEnviron(psi, ttno)
expr = hop_expr1(active_node, psi, ttno, ttne)
out = expr(active_node.tensor)
```

benchmark 中要分开记录：

- `time_env_build_sec`：`TTNEnviron(psi, ttno)`。
- `time_apply_sec`：`expr(active_tensor)`。
- 可选 `time_expr_build_sec`：`hop_expr1()` 构造 opt_einsum expression。

## Step 4：数值一致性

小系统：

- 比较 full dense `H|psi>`。
- 或比较 local effective Hamiltonian 对同一个 active tensor 的 action。

中等系统：

```text
relative_error =
|| action_method - action_ttno_with_env || / || action_ttno_with_env ||
```

如果 SOP-with-env 第一版只实现 one-site local action，benchmark 字段应明确写 `quantity=local_effective_1site_apply`，不要伪装成 full-state `H|psi>`。

## Step 5：benchmark 脚本

建议新增：

```text
benchmarks/benchmark_operator_env_paths.py
```

保留已有 `benchmarks/benchmark_sop_vs_ttno.py`，因为它仍可展示 full-state flat SOP vs TTNO apply。

新脚本字段建议：

```text
case_name
n_lead
n_phonon
n_sites
n_terms_sop
ttno_max_bond
state_max_bond
basis_info
active_node_idx
quantity
method
repeat_id
time_env_build_sec
time_expr_build_sec
time_apply_sec
time_total_sec
relative_error_vs_ttno
```

method 固定为：

```text
sop_no_env
sop_with_env
ttno_with_env
```

## Step 6：推荐验证命令

先跑单元测试：

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_baseline.py renormalizer/tn/tests/test_sop_baseline_dense.py renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py -q
```

再跑小 benchmark：

```bash
conda run -n reno-3.9 python benchmarks/benchmark_operator_env_paths.py --case lead --lead-list 1 2 --phonon 1 --repeats 2 --output benchmarks/results/dev_operator_env_paths.csv
```

## 风险与 fallback

- 如果通用 tree branch signature 太复杂，先固定 active node 为 junction bridge/root 附近节点。
- 如果 full-state `H|psi>` 的 SOP-with-env 不自然，先 benchmark local effective Hamiltonian；这是 TDVP/MCTDH 中 environment 真正服务的对象。
- 如果 fermionic `Z` string 的 branch signature 容易误缓存，测试必须覆盖 junction current / hopping terms。
