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
conda run -n reno-3.9 python benchmarks/benchmark_sop_vs_ttno.py --case lead --lead-list 1 2 --phonon 1 --repeats 2 --output benchmarks/results/dev_sop_vs_ttno.csv
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
raw_csv: benchmarks/results/adaptive_operator_env/sanity_114123_raw.csv
fit_csv: benchmarks/results/adaptive_operator_env/sanity_114123_fits.csv
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
raw_csv: benchmarks/results/adaptive_operator_env/sanity_114334_raw.csv
fit_csv: benchmarks/results/adaptive_operator_env/sanity_114334_fits.csv
```
