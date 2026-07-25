# Reflection: Slurm 激活顺序与 scaling 诊断

## 发生了什么

contraction diagnostic 初始 array job `115387` 中 tasks 0--7 成功，tasks 8--143
在真正运行 benchmark 前失败。原因是脚本在加载 Curie conda 环境之前启用了
`set -u`；环境初始化脚本引用了尚未定义的变量。

修正脚本顺序后，replacement array `115549` 补跑 tasks 8--143，最终形成
144/144 个 `status=ok` snapshots；dependent summary job `115555` 完成聚合。

## 可复用规则

Curie Slurm wrapper 必须按以下顺序：

```bash
source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9
set -u
```

shell syntax 检查不能发现初始化阶段的 nounset 问题。正式 array 前应增加一个
compute-node smoke task，并确认它生成预期 snapshot 后再提交生产数组。

## 科学诊断上的收获

不要仅根据一条 full-model wall-time 曲线给 tensor contraction 命名复杂度。
本轮把调查拆为：

1. shape-only optimized FLOPs；
2. isolated dense-kernel wall time；
3. full-model storage、memory 和 stage timing。

这个分层把“数学上 `M_s^4`、有限区间 wall time 更低”以及
“paired leaf `d^4`、primitive-contracted leaf `d^2`”区分开来，避免用单个经验
exponent替代 tensor-index 分析。
