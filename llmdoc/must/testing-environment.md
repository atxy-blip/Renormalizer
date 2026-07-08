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
```

这个变量需要在 import Renormalizer / NumPy 之前生效。
