# SOP Environment Benchmark 实现流程

目标是实现并 benchmark 三条路径：

```text
sop_no_env -> sop_with_env -> ttno_with_env
```

不要把物理 bath/lead/phonon environment 与 contraction environment 混淆。

## Step 1：保留并命名 naive SOP

当前 `SOPBaselineOperator.apply_to_ttns()` 默认是 flat SOP term-by-term apply，并已整理出显式 `apply_to_ttns_no_env()` 入口。

建议：

- 保留现有行为。
- benchmark method name 使用：`sop_no_env`。
- 文档里说明它没有 branch contraction cache，只缓存 local matrix factor。

这条路径用于展示不构造 environment 的重复 traversal / contraction 开销。

## Step 2：先实现 one-site SOP-with-env

最小可验证版本不覆盖完整 TDVP sweep，而是实现 active node 的 local effective Hamiltonian action。当前实现位置：

```text
benchmarks/benchmark_adaptive_operator_env.py::SOPOneSiteEffective
```

对应概念接口：

```text
build_sop_one_site_env(psi, sop, active_node)
apply_sop_one_site_env(env, active_tensor)
```

复用粒度建议：

- 对 active node 的每个 child branch 独立构造 environment。
- cache key 是 `(branch_root_idx, branch_signature)`。
- `branch_signature` 只记录该 branch subtree 内非 identity 的 local `Op`。
- 如果一个 SOP term 在该 branch 全是 identity，signature 为空，因此 identity branch environment 可跨 terms 复用。
- 多个 SOP terms 有相同 branch signature 时复用同一个 environment tensor。

第一版只支持 one-site active node。two-site active subtree 和完整 full-state `H|psi>` SOP-with-env 可后续扩展。

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

当前新增：

```text
benchmarks/benchmark_adaptive_operator_env.py
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
status
overhead_region
```

method 固定为：

```text
sop_no_env
sop_with_env
ttno_with_env
```

## Step 5.1：scaling path、basis 和 Hamiltonian term count

当前 adaptive benchmark 使用 Hubbard molecular junction builder：

```text
benchmarks/benchmark_adaptive_operator_env.py::build_hubbard_junction_case
```

两条 scaling path：

- `lead_only`
  - 扫描 `n_lead = 4, 8, 16, 32, 64, 128`；
  - 固定 `n_phonon = 0`；
  - 目的：隔离 fermionic lead modes 增长。
- `balanced_lead_phonon`
  - 扫描 `(n_lead, n_phonon) = (4,1), (8,2), (16,4), (32,8), (64,16)`；
  - lead 和 phonon 同时增加；
  - 目的：展示更接近 molecular junction 整体变大的 scaling。

每个 `n_lead` 会生成四组 fermionic lead mode：

```text
L_i, L^i, R_i, R^i  for i = 0 ... n_lead-1
```

所以 fermionic lead site 数是 `4 * n_lead`。再加 bridge 上两个 spin site：

```text
s^, s_
```

因此：

```text
n_fermion_sites = 4 * n_lead + 2
n_boson_sites = n_phonon
n_total_sites = 4 * n_lead + 2 + n_phonon
```

这里的 `site` 是 TTNS/TTNO 的物理自由度 site，不是 Hilbert space 总维数，也不是 local basis dimension。

`n_sop_terms` 是 Hamiltonian 的 SOP 求和项数：

```text
H = sum_alpha H_alpha
```

也就是 product operator summand 的个数。它不是 site 数，也不是 basis 数。

当前默认参数下，bridge onsite / Hubbard U 的系数为 0，经过 SOP simplify 后不计入 term count。每个 fermionic lead mode 贡献 3 个 product terms：

```text
1. lead onsite energy
2. lead -> bridge hopping
3. bridge -> lead hopping
```

fermionic lead mode 总数是 `4 * n_lead`，所以 lead 部分贡献：

```text
3 * (4 * n_lead) = 12 * n_lead
```

每个 phonon mode 贡献 4 个 product terms：

```text
1. p^2
2. x^2
3. n_{s^} * x
4. n_{s_} * x
```

所以本 benchmark 中：

```text
n_sop_terms = 12 * n_lead + 4 * n_phonon
```

例子：

```text
lead_only, n_lead=128, n_phonon=0:
  n_total_sites = 514
  n_sop_terms = 1536

balanced, n_lead=64, n_phonon=16:
  n_total_sites = 274
  n_sop_terms = 832
```

`ttno_max_bond` 是同一个 Hamiltonian 被压缩为 TTNO 后最大的 operator bond dimension。它反映 TTNO 是否成功共享了 SOP terms 之间的重复 operator structure；在 `large_114126` 结果中一直是 `7`。

## Step 5.2：alpha / scaling exponent 的含义

benchmark 的 scaling fit 使用经验幂律：

```text
t(N) = C * N^alpha
```

等价于：

```text
log t = alpha * log N + log C
```

因此 `alpha` 是 log-log 图上的斜率，不是物理模型参数。它必须和横轴一起报告，例如：

```text
alpha fitted against n_total_sites
alpha fitted against n_sop_terms
```

解释：

- `alpha ≈ 1`：近似线性 scaling，`N` 翻倍时 wall time 约翻倍；
- `alpha ≈ 1.5`：`N` 翻倍时 wall time 约变成 `2^1.5 ≈ 2.8` 倍；
- `alpha ≈ 2`：近似二次 scaling，`N` 翻倍时 wall time 约变成 4 倍。

正式报告优先使用 mean-per-size fit，而不是把每个 repeat 行直接放进 fit。当前脚本：

```text
benchmarks/plot_operator_env_scaling.py
```

会从 raw CSV 生成：

```text
*_formal_summary.csv
*_formal_mean_fits.csv
```

其中 `*_formal_mean_fits.csv` 是按每个尺寸先取 mean/std 再拟合，适合用于文字解释和图注。

`large_114126` 的 mean-per-size large-only 结果：

```text
lead_only, alpha vs n_total_sites:
  sop_no_env      2.071
  sop_with_env    1.382
  ttno_with_env   1.001

balanced_lead_phonon, alpha vs n_total_sites:
  sop_no_env      2.074
  sop_with_env    1.364
  ttno_with_env   1.000
```

这支持的解释是：

```text
Environment construction removes repeated contractions over the state tree,
while TTNO additionally removes repeated operator-structure redundancy across SOP terms.
```

## Step 6：Slurm CPU benchmark

不要在登录节点直接运行正式 benchmark。使用 CPU-only Slurm 脚本：

```bash
sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

默认 `RUN_PROFILE=sanity`，只做 correctness/smoke，不用于 scaling 结论。

中等规模趋势检查：

```bash
RUN_PROFILE=medium sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

大规模 scaling fit：

```bash
RUN_PROFILE=large sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

脚本固定 CPU backend：`RENO_GPU=cpu`、`RENO_NUM_THREADS=1`、`OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1`、`OPENBLAS_NUM_THREADS=1`。

输出：

- raw CSV：`benchmarks/results/adaptive_operator_env/<profile>_<jobid>_raw.csv`
- fit CSV：`benchmarks/results/adaptive_operator_env/<profile>_<jobid>_fits.csv`
- log-log time plots 和 operator diagnostics plots。

正式画图使用 plot 环境：

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -p /software/cache/yuxiong/plot \
python benchmarks/plot_operator_env_scaling.py \
  --raw benchmarks/results/adaptive_operator_env/large_114126_raw.csv \
  --output-prefix benchmarks/results/adaptive_operator_env/large_114126_formal
```

生成 PNG/PDF、mean summary CSV 和 mean-fit CSV。

`sanity` profile 只有两个尺寸点，fit CSV 会输出 exponent，但 `stable_vs_large=False`，不能拿来做 scaling 结论。

## 风险与 fallback

- 如果通用 tree branch signature 太复杂，先固定 active node 为 junction bridge/root 附近节点。
- 如果 full-state `H|psi>` 的 SOP-with-env 不自然，先 benchmark local effective Hamiltonian；这是 TDVP/MCTDH 中 environment 真正服务的对象。
- 如果 fermionic `Z` string 的 branch signature 容易误缓存，测试必须覆盖 junction current / hopping terms。
- 如果某个方法在大尺寸 timeout 或超过内存限制，adaptive benchmark 会记录当前点状态，并在后续更大点把该方法标记为 `skipped_after_previous_timeout_or_memory`，避免整条 job 因单个 baseline 崩溃。
