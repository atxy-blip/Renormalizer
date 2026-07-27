# SOP 线性学习清单设计

日期：2026-07-27

## 目标

生成一份 ADHD 友好的线性 Markdown 学习清单。学习者完成后，应当能够从头向老师说明：

1. 当前 SOP、strict state environment 和 TTNO 三条路径分别做了什么；
2. 为什么要增加 strict MCTDH-like state environment；
3. 每项修改产生了什么可观测效果；
4. 正式实验如何从 manifest、snapshot 进入 summary、fit 和论文图；
5. 哪张图属于主文，哪两张图属于 Supporting Information，以及各图支持什么结论。

## 采用方案

采用 12 个严格顺序的 45 分钟单元，总学习时间约 9 小时。不得跳过前置单元，也不设置并行支线。

每个单元使用相同的时间盒：

- 5 分钟：不看答案复述上一节；
- 25 分钟：运行 notebook、检查真实对象或使用指定断点；
- 10 分钟：填写公式、代码对象和观察结果；
- 5 分钟：形成可口述的三句话。

只有留下该节要求的具体证据后，才能勾选完成。

## 十二个单元

| 单元 | 主题 | 主要来源 | 必须形成的证据 |
| ---: | --- | --- | --- |
| 1 | 环境与实验地图 | notebook setup、Investigation 1 | 成功启动记录和完整数据流手绘/文字链 |
| 2 | `Op` 与 `SOPTerm` | Investigation 2 | 一个真实 term 的 coefficient 与 local factors 对照 |
| 3 | product term 到 tree node | Investigation 3 | `dof2idx` 映射和非平凡 node 编号 |
| 4 | symbolic operator 到局域矩阵 | Investigation 4 | `op_mat` 输入、输出 shape 与 physical axis 对照 |
| 5 | 完整 no-environment SOP apply | Investigation 5 | 13-term loop、最终求和和 bond 变化记录 |
| 6 | strict directed-edge state environment | Investigation 6 | cache key、entry 数和有向边含义 |
| 7 | term cache 与 signature cache | Investigation 7 | `91 → 33` 的原因及其非 strict 边界 |
| 8 | TTNO operator bond 与 environment | Investigation 8 | TTNO bond、environment shape 和复用对象 |
| 9 | 三条正式路径的正确性与计时边界 | Investigation 9 | 三个 method、status、误差和 quantity 表 |
| 10 | manifest 到正式图 | Investigation 10 | `189 → 63 → 18 → PDF/PNG` 数据链 |
| 11 | 主文与 SI 图件阅读 | 三张 Nature-style 图 | 每个 panel 的一句结论及科学边界 |
| 12 | 给老师的完整汇报演练 | notebook oral recap | 一次不看资料的 5–8 分钟口述和自检 |

## 最终清单格式

最终文件写入：

```text
llmdoc/guides/sop-linear-learning-checklist.md
```

每节包含：

1. Markdown 完成框；
2. 明确的 45 分钟分段；
3. 对应 notebook Investigation；
4. 必须执行的 cell、观察对象或断点；
5. 一个必须手写回答的问题；
6. 一个客观完成证据；
7. 三句话口述模板；
8. 卡住时的停止规则。

清单开头给出统一启动命令和使用规则，末尾提供一张总进度表及老师可能追问的问题。

## 图件分工

主文唯一推荐图：

```text
benchmarks/results/operator_env_scaling/final/
  li2024_spin_boson_20260713_scaling_three_panel.pdf
```

它承担三条正式方法在 `N_b`、`M_s`、`d` 三个方向上的核心比较。

Supporting Information：

```text
benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/
  complexity_validation.pdf
  model_mechanism.pdf
```

`complexity_validation.pdf` 支撑 `M_s^4`、paired-leaf `d^4` 和
primitive-contracted `d^2` 的数学/isolated-kernel解释。
`model_mechanism.pdf` 展示总时间、阶段时间、storage 和 memory，用于解释观测标度的机制。

PNG 是版式检查和预览副本；投稿使用对应 PDF。旧 `ren_formal_partial` 和缺失 raw CSV
的 historical strict-all-node 图不列入正式投稿图件。

## ADHD 约束

- 每次只显示和执行当前单元，不提前展开后续任务。
- 一个单元结束时无论是否完全理解都停止，记录卡点，不通过延长时间补偿。
- “运行过”不等于“完成”；必须留下文字、数值或口述证据。
- 卡住超过 10 分钟时，回到该节的 expected observation，记录实际值与预期值的第一处差异。
- 每次开始只要求完成一个 45 分钟单元，不使用“今天学完全部 SOP”作为任务描述。

## 验收标准

最终清单满足以下条件：

- 12 个单元严格线性编号，全部带 Markdown checkbox；
- 每节均能在 45 分钟内独立结束；
- 所有文件、函数、method label、数量和图件路径与当前仓库一致；
- 明确区分 full-state `H|psi>`、all-node local actions 和 full TDVP propagation；
- 明确区分 finite-window wall-time exponent 与 tensor FLOP complexity；
- 主文/SI 图件路径可以直接点击；
- 学习者完成最后一节后可按“修改—原因—效果—证据—边界”顺序口述。

