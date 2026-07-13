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

## 架构说明

- `llmdoc/architecture/op-to-contraction.md`：`Op` 如何变成局域矩阵、TTNO tensor、SOP term，并进入 contraction。
- `llmdoc/architecture/ttns-ttno-environment.md`：TTNS/TTNO environment 现有实现与 SOP baseline 缺口。

## 操作指南

- `llmdoc/guides/sop-environment-benchmark-flow.md`：实现三条 benchmark path 的建议流程。

## 参考索引

- `llmdoc/reference/key-files.md`：核心文件、类、函数索引。

## 记忆区

- `llmdoc/memory/decisions/2026-07-08-curie-reno39-testing.md`：固定使用 Curie `reno-3.9` 环境测试的决策记录。
- `llmdoc/memory/decisions/2026-07-09-operator-env-large-benchmark.md`：历史 root-only large benchmark 及其降级为归档数据源的原因。
- `llmdoc/memory/lessons-learned.md`：从已归档 reflection 提炼的 benchmark identity 与长作业规则。
- `llmdoc/memory/doc-gaps.md`：`M_s^3`、TTNO `d^4`、full-step timing 和 formal 缺失任务的闭合条件。
- `llmdoc/memory/reflections/`：后续阶段性反思记录。
  - `llmdoc/memory/reflections/2026-07-13-ren-formal-tree-scaling-gaps.md`：formal 三变量 partial 结果、与 Ren.J.2022 的对象差异和待诊断问题。
- `llmdoc/memory/archive/2026-07-13/`：已被 lessons 和稳定文档总结的 2026-07-10 原始 reflection。

`.llmdoc-tmp/` 是临时调查区，不属于稳定文档。
