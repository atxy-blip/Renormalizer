# llmdoc 索引

本目录记录当前 Reno-quantity 工作树中与 TTNS/TTNO/SOP operator baseline 相关的稳定项目知识。

## 启动入口

- `llmdoc/startup.md`：每次接手本仓库任务时先读。

## 必读约定

- `llmdoc/must/project-basics.md`：项目范围、当前分支背景、关键术语。
- `llmdoc/must/testing-environment.md`：Curie 本机测试环境约定。
- `llmdoc/must/ttns-sop-task-context.md`：本轮 SOP environment / benchmark 任务上下文。

## 项目概览

- `llmdoc/overview/project-overview.md`：Renormalizer 与本分支新增内容概览。
- `llmdoc/overview/scaling-benchmark-status.md`：legacy formal、contraction diagnostics 和 Li.W.2024 rerun 的当前完成状态、正文/SI 分工与主要拟合。

## 架构说明

- `llmdoc/architecture/op-to-contraction.md`：`Op` 如何变成局域矩阵、TTNO tensor、SOP term，并进入 contraction。
- `llmdoc/architecture/ttns-ttno-environment.md`：TTNS/TTNO environment 现有实现与 SOP baseline 缺口。
- `llmdoc/architecture/primitive-contraction-scaling.md`：paired phonon leaf 的 `d^4` 来源、primitive contraction 的 `d^2` 结构和 `M_s^4` internal-node FLOP 诊断。
- `llmdoc/architecture/paired-vs-contracted-leaves.md`：两种声子叶因子化的结构、d^4/d^2 来源、自适应切换规则与全模型跳变解读。

## 操作指南

- `llmdoc/guides/sop-environment-benchmark-flow.md`：实现三条 benchmark path 的建议流程。
- `llmdoc/guides/sop-debugging-lab.md`：执行十项 SOP debugging lab，并保持 formal
  timing object、method identity 和 scaling 结论的科学边界。
- `llmdoc/guides/sop-linear-learning-checklist.md`：按 12 个 45 分钟 Session
  线性完成 notebook 调试、实验数据链、论文图阅读和老师汇报演练。

## 参考索引

- `llmdoc/reference/key-files.md`：核心文件、类、函数索引。
- `llmdoc/reference/plotting-style-guide.md`：formal benchmark figure 的共享
  Nature-style typography、语义编码、固定版式、导出策略与复现命令。

## 记忆区

- `llmdoc/memory/decisions/2026-07-08-curie-reno39-testing.md`：固定使用 Curie `reno-3.9` 环境测试的决策记录。
- `llmdoc/memory/decisions/2026-07-09-operator-env-large-benchmark.md`：历史 root-only large benchmark 及其降级为归档数据源的原因。
- `llmdoc/memory/lessons-learned.md`：从已归档 reflection 提炼的 benchmark identity 与长作业规则。
- `llmdoc/memory/doc-gaps.md`：正文/SI 分工、刻意边界和 legacy formal 处置的闭合条件。
- `llmdoc/memory/reflections/`：后续阶段性反思记录。
  - `llmdoc/memory/reflections/2026-07-13-ren-formal-tree-scaling-gaps.md`：formal 三变量 partial 结果、与 Ren.J.2022 的对象差异和待诊断问题。
  - `llmdoc/memory/reflections/2026-07-24-slurm-activation-and-scaling-diagnosis.md`：Curie conda/nounset 顺序故障和分层 scaling 诊断方法。
  - `llmdoc/memory/reflections/2026-08-06-main-si-slurm-activation-repeat.md`：main/SI 分工与 Slurm wrapper 激活顺序重复错误的修正记录。
- `llmdoc/memory/archive/2026-07-13/`：已被 lessons 和稳定文档总结的 2026-07-10 原始 reflection。

`.llmdoc-tmp/` 是临时调查区，不属于稳定文档。
