# 测试环境约定

在 Curie 本机运行本仓库测试和 benchmark 时，统一使用 conda 环境：

```bash
conda run -n reno-3.9 python ...
```

已验证：

```text
Python 3.9.20
```

## 推荐命令

SOP baseline 快速测试：

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_baseline.py -q
```

SOP dense / TTNO equivalence 测试：

```bash
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_baseline_dense.py renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py -q
```

benchmark 小规模试跑：

```bash
conda run -n reno-3.9 python benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py --case lead --lead-list 1 2 --phonon 1 --repeats 2 --output benchmarks/results/dev_sop_vs_ttno.csv
```

## 注意事项

- 不使用裸 `python`。当前 shell 中裸 `python` 不存在。
- 如果只做只读源码调查，可用 `python3` 执行短脚本；正式测试和 benchmark 必须使用 `reno-3.9`。
- 为降低 BLAS 线程差异，benchmark 前优先设置：

```bash
export RENO_NUM_THREADS=1
export RENO_GPU=cpu
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
```

这些变量需要在 import Renormalizer / NumPy 之前生效。`RENO_GPU=cpu` 会显式跳过 CuPy 初始化，避免在 CPU 节点上先尝试 CUDA 再回退 NumPy。

## Curie Slurm CPU 验证

不要在登录节点直接运行正式测试。当前提供 CPU-only Slurm 验证脚本：

```bash
sbatch benchmarks/scripts/curie_cpu_sop_validation.sbatch
```

该脚本参考 `/software/sbatch_examples/python_example.sbatch`：

- 使用 `source /software/envs/bash.profile` 和 `source /software/envs/anaconda3.env`；
- 激活 `reno-3.9`；
- 提交到 `CPU` 分区；
- 只申请 1 个 CPU 核；
- 申请 64GB 内存；
- 设置 `RENO_GPU=cpu`、`RENO_NUM_THREADS=1`、`OMP_NUM_THREADS=1`、`MKL_NUM_THREADS=1`、`OPENBLAS_NUM_THREADS=1`；
- 运行 SOP/TTNO correctness 相关 py_compile 和 pytest。

最近一次验证记录：

```text
job_id: 114122
node: curie-cpu001
status: COMPLETED
exit_code: 0:0
result: 14 passed in 6.32s
log: benchmarks/results/slurm_logs/sop_cpu_validation_114122.log
```

## Curie Slurm Adaptive Benchmark

当前 adaptive benchmark 脚本：

```bash
sbatch benchmarks/scripts/curie_cpu_adaptive_operator_env.sbatch
```

profile：

- `RUN_PROFILE=sanity`：小尺寸 correctness/smoke，不用于 scaling 结论；
- `RUN_PROFILE=medium`：服务器中等规模趋势检查；
- `RUN_PROFILE=large`：服务器大尺寸 log-log fitting。

可用环境变量选择 timing object：

```bash
ACTIVE_SCOPE=root      # root one-site local effective Hamiltonian action
ACTIVE_SCOPE=all_nodes # all-node sweep-like collection of one-site actions
```

strict MCTDH-like SOP baseline 的 scaling 诊断应使用 `ACTIVE_SCOPE=all_nodes`。root-only benchmark 不能用来验证 no-env `N^3`。

最近一次 sanity 记录：

```text
job_id: 114123
node: curie-cpu001
status: COMPLETED
exit_code: 0:0
backend: RENO_GPU='cpu'; Use NumPy as backend
raw_rows: 12
max_relative_error_vs_ttno: about 8e-16
raw_csv: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/sanity_114123_raw.csv
fit_csv: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/sanity_114123_fits.csv
```

strict MCTDH-like all-nodes sanity 记录：

```text
job_id: 114334
node: curie-cpu011
status: COMPLETED
exit_code: 0:0
active_scope: all_nodes
scaling_path: lead_only
lead_values: 1 2 4 8
result:
  sop_no_env                  large-only alpha vs n_lead ~= 3.02
  sop_mctdh_like_state_env    large-only alpha vs n_lead ~= 2.03
  ttno_with_env               large-only alpha vs n_lead ~= 1.01
raw_csv: benchmarks/results/operator_env_scaling/archive/strict_all_nodes_development/sanity_114334_raw.csv
fit_csv: benchmarks/results/operator_env_scaling/archive/strict_all_nodes_development/sanity_114334_fits.csv
```

最终 strict all-nodes 记录：

```text
job_id: 114336
node: curie-cpu011
status: COMPLETED
exit_code: 0:0
active_scope: all_nodes
scaling_path: lead_only
n_total_sites: 18 34 66
fit_vs_n_total_sites:
  sop_no_env                  alpha = 3.246
  sop_mctdh_like_state_env    alpha = 2.167
  ttno_with_env               alpha = 1.063
result_dir: benchmarks/results/operator_env_scaling/final/
```

当前 large 三变量补充任务：

```text
job_id: 114439
submitted: 2026-07-10
active_scope: all_nodes
scaling_path: lead_only
purpose: 扩大 N_site 点数，补足 medium 只有 3 点的问题
expected_outputs:
  benchmarks/results/operator_env_scaling/runs/large_114439_raw.csv
  benchmarks/results/operator_env_scaling/runs/large_114439_fits.csv
  benchmarks/results/operator_env_scaling/runs/adaptive_operator_env_114439.log

job_id: 114440
submitted: 2026-07-10
active_scope: all_nodes
scaling_path: ren_aux
purpose: 补充 Ren.J.2022 风格三变量图中的 M_s 和 d scaling
expected_outputs:
  benchmarks/results/operator_env_scaling/runs/large_114440_raw.csv
  benchmarks/results/operator_env_scaling/runs/large_114440_fits.csv
  benchmarks/results/operator_env_scaling/runs/adaptive_operator_env_114440.log
```

`ren_aux` 只包含 `state_bond` 和 `primitive_basis` path；后续需要与
`lead_only` raw 合并后，再用 `benchmarks/plot_operator_env_scaling.py`
生成完整三 panel PDF。

2026-07-12 提交的 recoverable 分片任务：

```text
114776: lead_only, n_lead = 4 8 16
114777: lead_only, n_lead = 32
114778: state_bond, M_s = 4 8 16 32 64, fixed n_lead = 4
114779: primitive_basis, d = 4 8 16 32, fixed n_lead = 1,
        n_phonon = 16, state M_s = 16
```

这些任务使用 repeat-level raw CSV checkpoint。正式分析仍需等待作业结束后检查
status、repeat 完整性和 relative error；checkpoint 中单一 x 值产生的临时 fit
及 `RankWarning` 不用于 scaling 结论。

2026-07-13 Ren-style formal Tree benchmark：

```text
job_id: 115005
array_tasks: 216
snapshot_root: benchmarks/results/operator_env_scaling/ren_formal/snapshots/
manifest: benchmarks/results/operator_env_scaling/ren_formal/manifest.tsv
```

每个 `(panel, method, point, repeat)` 独立运行并原子写 JSON-backed NPZ。
job 114789 因 runner 使用文件路径启动导致 `benchmarks` package import 失败，已
取消；115005 改用 `python -m benchmarks.run_ren_formal_point` 后已验证生成
`status=ok` 快照。

截至 2026-07-13 的落盘状态：

```text
available_snapshots: 204 / 216
available_status: all ok
missing:
  modes / sop_no_env / N_total_sites=300: 3 repeats
  state_bond / all methods / M_s=300: 9 repeats
frozen_partial_raw:
  benchmarks/results/operator_env_scaling/ren_formal/partial_20260713_raw.csv
partial_pdf:
  benchmarks/results/operator_env_scaling/final/ren_formal_partial_20260713_scaling_three_panel.pdf
```

formal 参数由 manifest 固定：

```text
N panel:   M_s=20, d=10, N_total_sites=18 30 46 74 118 186 300
M_s panel: N_phonon=16, d=10, M_s=10 20 30 50 70 100 150 220 300
d panel:   N_phonon=16, M_s=20, d=5 10 20 30 40 50 70 100
```

当前 partial fit 的重点是 N panel 约为 `N^3/N^2/N`；大 `M_s` 区间三条方法
均约 `M_s^3`；大 `d` 区间 SOP 近常数、TTNO 约 `d^4`。后两项必须保留为
与 Ren.J.2022 不同 timing object/algorithm 的待解释问题，不能仅凭参考虚线定论。

旧路径 `benchmarks/results/adaptive_operator_env/` 已整理为语义归档。正式图
只生成 PDF，并排除 `sop_env_plus_operator_cache`。当前 formal partial 输出：

```text
benchmarks/results/operator_env_scaling/final/ren_formal_partial_20260713_scaling_three_panel.pdf
```

## Curie shell 激活顺序

Slurm wrapper 必须在启用 nounset 前完成 Curie 环境初始化：

```bash
source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9
set -u
```

contraction diagnostic 初始 array `115387` 的 tasks 8--143 因顺序相反而在
conda activation 阶段失败。修正后的 replacement array `115549` 成功补齐，
最终为 144/144 个 `status=ok` snapshots。生产 array 前应先提交一个
compute-node smoke task，并检查它实际生成 snapshot。

## 最新完成的正式任务

Contraction diagnostics：

```text
initial: 115387, tasks 0--7 completed
replacement: 115549, tasks 8--143 completed
summary: 115555
final snapshots: 144 / 144, all ok
```

Li.W.2024 spin-boson rerun：

```text
compute-node smoke: 115694
production array: 115695
finalizer: 115708
final snapshots: 189 / 189, all ok
```

这两组结果和当前验证命令见：

```text
llmdoc/overview/scaling-benchmark-status.md
benchmarks/results/operator_env_scaling/runs/README.md
```
