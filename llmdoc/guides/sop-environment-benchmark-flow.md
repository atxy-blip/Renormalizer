# SOP Environment Benchmark 实现流程

目标是实现并 benchmark 四条路径：

```text
sop_no_env
sop_mctdh_like_state_env
sop_env_plus_operator_cache
ttno_with_env
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

注意：branch signature cache 不是 strict MCTDH-like baseline。它会把相同 operator subtree 的不同 SOP terms 合并为一个 cached branch environment，应标为：

```text
sop_env_plus_operator_cache
```

## Step 2.1：strict MCTDH-like all-nodes state environment

导师预期的 fair SOP/MCTDH-like baseline 需要保留 flat SOP term structure，但在一次 sweep-like all-nodes 计算中复用 state/mean-field environment。

当前实现位置：

```text
benchmarks/benchmark_adaptive_operator_env.py::SOPMCTDHSweepEnvironment
```

构造规则：

- 对每个 SOP term 单独处理；
- 对每条 tree edge 构造两个方向的 message；
- cache key 为 `(source_node_idx, target_node_idx, term_index)`；
- 不使用 branch operator signature；
- 不使用 TTNO/MPO operator bond；
- 不跨 product terms 合并相同 operator structure。

all-nodes 下应满足：

```text
n_env_cache_entries = n_sop_terms * 2 * (n_active_nodes - 1)
```

这个 invariant 由测试固定：

```text
renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py::test_strict_mctdh_state_env_reuses_term_messages_across_active_nodes
```

复杂度口径：

```text
sop_no_env(all_nodes)               ~ n_active_nodes * n_sop_terms * n_tree ~ N^3
sop_mctdh_like_state_env(all_nodes) ~ n_sop_terms * n_tree                  ~ N^2
ttno_with_env(all_nodes)            ~ N, if TTNO bond stays bounded
```

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

旧 full-state flat SOP vs TTNO apply 已归档到 `benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`。

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
sop_mctdh_like_state_env
sop_env_plus_operator_cache
ttno_with_env
```

`sop_with_env` 是旧的 ambiguous label。新 benchmark 中不应把它作为正式报告 label。

## Step 5.1：scaling path、basis 和 Hamiltonian term count

当前 adaptive benchmark 使用 Hubbard molecular junction builder：

```text
benchmarks/benchmark_adaptive_operator_env.py::build_hubbard_junction_case
```

基础 scaling path：

- `lead_only`
  - 扫描 `n_lead = 4, 8, 16, 32, 64, 128`；
  - 固定 `n_phonon = 0`；
  - 目的：隔离 fermionic lead modes 增长。
- `balanced_lead_phonon`
  - 扫描 `(n_lead, n_phonon) = (4,1), (8,2), (16,4), (32,8), (64,16)`；
  - lead 和 phonon 同时增加；
  - 目的：展示更接近 molecular junction 整体变大的 scaling。

Ren.J.2022 风格三变量图使用三类 path：

- `lead_only`：扫描 site number `N_site`。
- `state_bond`：固定 Hamiltonian size，扫描 TTNS random state 的 state bond dimension `M_s`。
- `primitive_basis`：固定 lead/phonon 数，强制 phonon primitive basis dimension `d`。

组合 path：

- `ren_aux`：只跑 `state_bond` 和 `primitive_basis`，适合和已有 `lead_only`
  结果合并成三 panel 图。
- `ren_variables`：一次跑 `lead_only`、`state_bond` 和 `primitive_basis`。

历史 adaptive large 默认：

```text
STATE_BOND_VALUES = 1 2 4 8 16
PRIMITIVE_BASIS_VALUES = 2 4 8 16
STATE_BOND_BASE_LEAD = 8
STATE_BOND_BASE_PHONON = 0
PRIMITIVE_BASIS_BASE_LEAD = 4
PRIMITIVE_BASIS_BASE_PHONON = 4
```

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

## Step 5.2：最终三 panel PDF

当前 publication plotter：

```text
benchmarks/plot_operator_env_scaling.py
```

输出单个 PDF：

```text
<output-prefix>_scaling_three_panel.pdf
```

三个 panel 分别使用：

```text
N panel:   x_axis = n_total_sites
M_s panel: x_axis = state_max_bond
d panel:   x_axis = primitive_basis_dim
```

正式图只包含：

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

`sop_env_plus_operator_cache` 不进入最终图。固定参考线画为虚线但不进入
legend，标注直接放在线旁。当前约定：

```text
N panel:   no-env N^3, strict SOP N^2, TTNO N^1
M_s panel: 三种方法均画 M_s^3
d panel:   两条 SOP 画常数，TTNO 画 d^4
```

`M_s` 和 `d` 参考线只覆盖后半数据，并与各曲线最后一个可用点重合。它们用于
帮助读图，不是拟合值，也不能替代对 Ren.J.2022 指数差异的解释。legend 放在第一
个 panel 内部，顶部不显示 fit alpha。

`ttno_max_bond` 是同一个 Hamiltonian 被压缩为 TTNO 后最大的 operator bond dimension。它反映 TTNO 是否成功共享了 SOP terms 之间的重复 operator structure；在 `large_114126` 结果中一直是 `7`。

## Step 5.3：长作业增量落盘

`run_benchmark()` 在每个 repeat 完成后原子更新 raw CSV，在每个 size point
完成后更新 fit CSV。Slurm time limit 或外部中断最多丢失当前 repeat，已经完成
的 repeat 不应再像 job 114439 一样全部丢失。

长时间的 `lead_only` all-nodes 测试应按尺寸拆分作业。`n_lead=32` 已经需要
数小时，不应与 `n_lead=64/128` 放在同一个 12 小时 allocation 中。

只有 `N_site` panel 的 `N^3/N^2/N` 是本 benchmark strict algorithm identity
直接支持的复杂度口径。Ren.J.2022 中的 `M_s^4` 和 `d^2` 分别属于 binary
ML-MCTDH 和 MPS TD-DMRG 的特定实现/计算对象，不能直接映射到本仓库三种
Tree operator representation。当前图上的 `M_s^3` 和 TTNO `d^4` 是已有数据的
视觉参考，差异本身必须继续诊断。

## Step 5.4：Ren-style formal Tree array

正式参数清单在：

```text
benchmarks/ren_formal_manifest.py
```

参数固定为：

```text
N panel:   M_s=20, d=10, N_total_sites=18,30,46,74,118,186,300
M_s panel: N_phonon=16, d=10, M_s=10,20,30,50,70,100,150,220,300
d panel:   N_phonon=16, M_s=20, d=5,10,20,30,40,50,70,100
```

每个方法、点和 repeat 是一个独立 array task：

```bash
sbatch benchmarks/scripts/curie_cpu_ren_formal_array.sbatch
```

runner 必须用 module mode 启动：

```bash
python -m benchmarks.run_ren_formal_point ...
```

不要改回 `python benchmarks/run_ren_formal_point.py`，否则在计算节点可能找不到
`benchmarks` package。每个任务原子写到：

```text
benchmarks/results/operator_env_scaling/ren_formal/snapshots/<panel>/<method>/*.npz
```

NPZ 内保存 JSON payload 且 `allow_pickle=False`。聚合器必须允许缺失任务并明确
列出缺口；只有 216/216 且全部 `status=ok` 才可命名为 final result。

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

历史 root-only benchmark (`large_114126`) 的 mean-per-size large-only 结果：

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

这些结果只适合解释 root one-site kernel。因为 root-only `sop_no_env` 理论上就是：

```text
n_sop_terms * n_tree ~ N^2
```

因此不能拿 root-only 结果验证 no-env `N^3`。

strict MCTDH-like all-nodes sanity (`n_lead=1,2,4,8`) 的关键结果：

```text
fit vs n_lead, large-only:
  sop_no_env                  3.02
  sop_mctdh_like_state_env    2.03
  sop_env_plus_operator_cache 2.43
  ttno_with_env               1.01
```

解释口径：

```text
active_scope=root:
  root one-site kernel; no-env expected ~ N^2

active_scope=all_nodes:
  sweep-like collection of one-site kernels; no-env expected ~ N^3
  strict MCTDH-like state env expected ~ N^2
  TTNO with bounded operator bond expected ~ N
```

## Step 5.3：最终发布图与结果目录

当前正式发布数据源是 all-nodes job 114336：

```text
benchmarks/results/operator_env_scaling/final/
  strict_all_nodes_medium_114336_raw.csv
  strict_all_nodes_medium_114336_summary.csv
  strict_all_nodes_medium_114336_fits.csv
  strict_all_nodes_medium_114336_scaling_vs_nsite.pdf
```

PDF 只显示：

```text
sop_no_env
sop_mctdh_like_state_env
ttno_with_env
```

横轴固定为 `N_total_sites`，图中用虚线给出 `alpha=3,2,1` 的理论斜率
参考。`sop_env_plus_operator_cache` 是实现过程中的中间路径，保留在 raw
CSV 和开发归档中，但不进入正式图。

历史结果按 timing object 归档到：

```text
benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/
benchmarks/results/operator_env_scaling/archive/strict_all_nodes_development/
benchmarks/results/operator_env_scaling/archive/legacy_sop_vs_ttno/
```

不要因为 root-only run 使用 `large` profile 就把它当作最终 scaling 结果。

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

选择 timing object：

```bash
ACTIVE_SCOPE=root      # root one-site kernel
ACTIVE_SCOPE=all_nodes # sweep-like all-node local effective action
```

strict MCTDH-like scaling 诊断应使用：

```bash
ACTIVE_SCOPE=all_nodes SCALING_PATH=lead_only RUN_PROFILE=sanity \
LEAD_VALUES="1 2 4 8" REPEATS=1 MAX_EXTRA_POINTS=0 \
sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

输出：

- raw CSV：`benchmarks/results/operator_env_scaling/runs/<profile>_<jobid>_raw.csv`
- fit CSV：`benchmarks/results/operator_env_scaling/runs/<profile>_<jobid>_fits.csv`
- run-level PNG diagnostics（只用于筛选，不作为正式图）。

正式画图使用 plot 环境：

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -p /software/cache/yuxiong/plot \
python benchmarks/plot_operator_env_scaling.py \
  --raw benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/final/strict_all_nodes_medium_114336
```

生成 summary CSV、fit CSV 和一张 PDF，不生成 PNG。当前正式 plotter 只接受
all-nodes 数据，并排除 `sop_env_plus_operator_cache`。

`sanity` profile 只有两个尺寸点，fit CSV 会输出 exponent，但 `stable_vs_large=False`，不能拿来做 scaling 结论。

## Step 7：Contraction diagnostics

当 full-model wall-time exponent 与预期 tensor-index complexity 不一致时，不要
直接调整参考线。使用三层诊断：

```text
1. shape-only optimized FLOPs / largest intermediate
2. isolated dense-kernel wall time
3. full-model storage, memory, build/env/apply stage timing
```

当前入口：

```bash
sbatch benchmarks/scripts/curie_cpu_contraction_scaling_diagnostics.sbatch
```

manifest 有 144 个独立任务。聚合和作图分别使用：

```bash
sbatch benchmarks/scripts/curie_cpu_contraction_scaling_summary.sbatch
conda run -n reno-3.9 python -m benchmarks.plot_contraction_scaling_diagnostics ...
```

正式解释见 `llmdoc/architecture/primitive-contraction-scaling.md`。

## Step 8：Li.W.2024 spin-boson formal rerun

模型和 adaptive topology：

```text
sub-Ohmic: s=0.5, omega_c=20 Delta, alpha=0.05, Delta=1
modes:      N_b=4,8,16,32,64,128,256; M_s=20; d=10
state bond: M_s=4,8,16,32,50,70,100; N_b=16; d=10
primitive:  d=4,8,16,32,50,70,100; N_b=16; M_s=20
contract primitive exactly when d > M_s
```

工作流：

```bash
conda run -n reno-3.9 python -m benchmarks.li2024_formal_manifest \
  --output benchmarks/results/operator_env_scaling/li2024_formal/manifest.tsv

sbatch benchmarks/scripts/curie_cpu_li2024_formal_array.sbatch
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```

每个 `(panel, method, point, repeat)` 原子写一个 snapshot。finalizer 只有在
189/189 task IDs 全部存在且 `status=ok` 时才输出 final aggregate/PDF。

注意：primitive contraction 会改变 tree topology 和 active-node 数。跨 topology
switch 的全区间 fit 只描述 end-to-end workflow；解释 large-`d` complexity 时必须
同时引用 isolated leaf FLOPs 和 TTNO storage。

正文/SI 分工（2026-08-06）：

- 正文三 panel 图只对 `modes` 报 `N_b^3/N_b^2/N_b`；`state_bond` 与
  `primitive_basis` 只作稳健性检查（不报指数、不画幂次参考线），并标注
  d > M_s topology switch。
- SI 图保留全部 panel 的 largest-four fits 与幂次参考线（M_s^4、常数），
  供审稿人复核；这些是有效 wall-time 指数，不是渐近 FLOP 指数。
- artifact 再生成用 Slurm finalizer：

```bash
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```

不重跑 189 个 snapshot。

## 风险与 fallback

- 如果通用 tree branch signature 太复杂，先固定 active node 为 junction bridge/root 附近节点。
- 如果 full-state `H|psi>` 的 SOP-with-env 不自然，先 benchmark local effective Hamiltonian；这是 TDVP/MCTDH 中 environment 真正服务的对象。
- 如果 fermionic `Z` string 的 branch signature 容易误缓存，测试必须覆盖 junction current / hopping terms。
- 如果某个方法在大尺寸 timeout 或超过内存限制，adaptive benchmark 会记录当前点状态，并在后续更大点把该方法标记为 `skipped_after_previous_timeout_or_memory`，避免整条 job 因单个 baseline 崩溃。
