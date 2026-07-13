# Reflection: Ren-style three-variable scaling

## 背景

Ren.J.2022 的 benchmark 图同时比较 state bond dimension `M_s`、site
number `N` 和 primitive basis dimension `d` 三个变量。当前 strict
all-nodes benchmark 原本只稳定产出 `lead_only` 的 `N_site` scaling，因此
中等规模三点图虽然能验证 `N^3/N^2/N` 口径，但不能直接复刻三变量展示。

## 关键教训

不要把三变量图只当成 plotter 改动。`M_s` 和 `d` 必须在 benchmark 层变成
独立 scaling path，否则图上只能出现空 panel 或把错误变量混到一起。

新增 path 的职责应保持清楚：

- `lead_only`：扫描 `N_site`。
- `state_bond`：固定 Hamiltonian size，扫描随机 TTNS state bond `M_s`。
- `primitive_basis`：固定 lead/phonon 数，强制 phonon primitive basis `d`。
- `ren_aux`：只跑 `state_bond` 和 `primitive_basis`，用于和已提交的
  `lead_only` large 结果合并。
- `ren_variables`：一次跑三类变量，适合重新生成完整三变量数据。

## 当前状态

本轮已提交两个 large Slurm job：

```text
114439: RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=lead_only
114440: RUN_PROFILE=large ACTIVE_SCOPE=all_nodes SCALING_PATH=ren_aux
```

plotter 输出改为单个三并排 PDF，并把理论虚线标注写在图内，例如
`\propto N^3`、`\propto M_s^2`、`\propto d^1`，不再把虚线含义塞进 legend。
