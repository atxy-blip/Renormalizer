# 2026-07-09 Operator Environment Large Benchmark

> 2026-07-10 状态：本文件记录的是历史 root-only benchmark，不再作为
> strict `N^3/N^2/N` 主图数据源。相关文件已归档到
> `benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/`。
> 当前最终 all-nodes 数据源是 job 114336，见
> `benchmarks/results/operator_env_scaling/README.md`。

## 背景

目标不是简单证明 TTNO 比 SOP 快，而是区分三条递进路径：

```text
sop_no_env -> sop_with_env -> ttno_with_env
```

解释重点：

```text
Environment construction removes repeated contractions over the state tree,
while TTNO additionally removes repeated operator-structure redundancy across SOP terms.
```

## 运行记录

Slurm job：

```text
job_id: 114126
profile: large
backend: CPU / NumPy
cores: 1
elapsed: 00:54:07
status: COMPLETED
```

输入和输出：

```text
raw_csv: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_raw.csv
raw_fit_csv: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_fits.csv
formal_summary: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_formal_summary.csv
formal_mean_fit: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_formal_mean_fits.csv
formal_figures_prefix: benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_formal_*.png/pdf
```

以下是 2026-07-09 当时使用的生成命令记录。当前 plotter 已收窄为 strict
all-nodes 三方法正式图，不再用于重新生成这组 root-only 历史图；原图已完整
保存在归档目录。

```bash
env MPLCONFIGDIR=/tmp/matplotlib-operator-env \
conda run -p /software/cache/yuxiong/plot \
python benchmarks/plot_operator_env_scaling.py \
  --raw benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_raw.csv \
  --output-prefix benchmarks/results/operator_env_scaling/archive/root_one_site_legacy/large_114126_formal
```

## scaling path 定义

`lead_only`：

```text
n_lead = 4, 8, 16, 32, 64, 128
n_phonon = 0
```

`balanced_lead_phonon`：

```text
(n_lead, n_phonon) = (4,1), (8,2), (16,4), (32,8), (64,16)
```

site 和 term count：

```text
n_total_sites = 4 * n_lead + 2 + n_phonon
n_sop_terms = 12 * n_lead + 4 * n_phonon
```

`n_total_sites` 是 TTNS/TTNO 物理自由度 site 数。`n_sop_terms` 是 Hamiltonian 的 SOP product operator summand 数，不是 site 数或 local basis 维数。

## 正确性

三条路径都完成，无 timeout / memory skip。

最大相对误差：

```text
lead_only: 3.62e-15
balanced_lead_phonon: 1.68e-15
```

## mean-per-size large-only scaling

报告时优先使用 `large_114126_formal_mean_fits.csv`，因为它先对每个尺寸的 repeats 求 mean/std，再做 log-log fit。

拟合形式：

```text
t(N) = C * N^alpha
```

`alpha` 是 log-log wall-time scaling exponent，必须说明横轴。

以 `n_total_sites` 为横轴：

```text
lead_only:
  sop_no_env      alpha = 2.071
  sop_with_env    alpha = 1.382
  ttno_with_env   alpha = 1.001

balanced_lead_phonon:
  sop_no_env      alpha = 2.074
  sop_with_env    alpha = 1.364
  ttno_with_env   alpha = 1.000
```

以 `n_sop_terms` 为横轴：

```text
lead_only:
  sop_no_env      alpha = 2.054
  sop_with_env    alpha = 1.370
  ttno_with_env   alpha = 0.993

balanced_lead_phonon:
  sop_no_env      alpha = 2.041
  sop_with_env    alpha = 1.343
  ttno_with_env   alpha = 0.985
```

## 解释

这组数据支持递进关系：

```text
sop_no_env:
  每个 SOP term 重新处理 state tree contraction，scaling 约 N^2。

sop_with_env:
  复用 active node 外部 branch environment，减少 state tree 上重复 contraction，scaling 降到约 N^1.35。

ttno_with_env:
  进一步用 TTNO operator bond 共享 SOP terms 间重复 operator structure。当前模型中 ttno_max_bond = 7，scaling 接近 N^1。
```

注意：当前 `sop_with_env` benchmark 是 one-site local effective Hamiltonian action，不是完整 full-state `H|psi>` 或完整 TDVP sweep。

## 与最终 strict 图的关系

本 run 的 `sop_with_env` 使用 operator-signature cache，后来重命名为
`sop_env_plus_operator_cache`。它不是 strict MCTDH-like baseline。最终图不
显示该中间路径，只显示 all-nodes `sop_no_env`、
`sop_mctdh_like_state_env` 和 `ttno_with_env`，并提供理论斜率
`alpha=3,2,1` 作为虚线参考。
