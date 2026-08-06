# 2026-08-06：main/SI 分工与 Slurm 激活顺序重复错误

## 背景

本轮把 Li.W.2024 operator-scaling 结果重新定位为“TTNO local action kernel
高度优化”的窄口径叙事：正文只报 `modes` panel 指数，M_s/d 作为参数稳健性
检查；指数与幂次参考线保留在 SI。绘图契约重构为
`benchmarks/plot_li2024_operator_scaling.py` 的 `main`/`si` 两种 figure mode，
finalizer 通过 Slurm 一次性生成两套 artifacts。

## 工作流教训：Slurm wrapper 激活顺序再次踩坑

新建的 `curie_cpu_operator_scaling_validation.sbatch` 在 `conda activate`
之前就执行了 `set -euo pipefail`，导致
`QT_XCB_GL_INTEGRATION: unbound variable`，job 121980 FAILED。
这是 2026-07-24 reflection 已记录过的错误；修正为 finalize wrapper 的
`source → conda activate → set -u` 顺序后，job 121981 COMPLETED（39 passed）。

**规则**：任何新的 Curie sbatch wrapper 必须复制
`curie_cpu_li2024_formal_finalize.sbatch` 的激活顺序：
先 `source /software/envs/bash.profile`、`source /software/envs/anaconda3.env`、
`conda activate reno-3.9`，最后才 `set -u`。提交前先用 compute-node smoke
验证，不要只在登录节点语法检查。

## 数据/制品约定

- `benchmarks/results/**/*.csv` 被 `.gitignore` 忽略，CSV 由 Slurm finalizer
  从 snapshots 再生成，不入库；只有 PDF/PNG 图件用 `git add -f` 入库。
- finalizer 现在同时写 main fits（6 行，仅 modes）与 SI fits（18 行，三
  panel），以及 main/SI 两套 PDF/PNG。

## 状态

llmdoc 稳定文档已同步 main/SI 分工；遗留项只有 legacy 204/216 Hubbard array
的归档处置（见 `llmdoc/memory/doc-gaps.md`）。
