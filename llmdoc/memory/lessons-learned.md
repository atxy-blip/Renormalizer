# Lessons Learned

Curated cross-task rules distilled from archived memory.

## Benchmark identity

### Always name the timing object
**Rule**: 每个 scaling exponent 必须同时报告 active scope、timed quantity 和横轴变量。
**Why**: root one-site kernel 与 all-node sweep-like kernel 相差一个 active-node 因子，曾导致把正确的 `N^2` 误判为缺少预期的 `N^3`。
**Source**: `llmdoc/memory/archive/2026-07-13/2026-07-10-strict-mctdh-sop-baseline.md`

### Separate state reuse from operator reuse
**Rule**: strict MCTDH-like SOP 必须保留 term index，并把 operator-signature cache 单独命名。
**Why**: branch-signature grouping 会跨 SOP terms 复用 operator structure，不能代表只复用 mean-field/state environment 的 baseline。
**Source**: `llmdoc/memory/archive/2026-07-13/2026-07-10-strict-mctdh-sop-baseline.md`

### Archive by algorithm identity
**Rule**: benchmark 结果按算法身份和 timing object 归档，profile 和 Slurm job id 只作为运行元数据。
**Why**: 名为 large 的 root-only 结果曾容易被误认为 strict all-node 最终数据。
**Source**: `llmdoc/memory/archive/2026-07-13/2026-07-10-operator-scaling-result-archive.md`

## Long-running experiments

### Persist every independent repeat
**Rule**: 长 benchmark 的最小独立任务必须原子落盘，聚合和拟合在任务外完成。
**Why**: 只在整项工作结束时写 CSV 会在 Slurm timeout 后丢失全部已完成计算；正式数组已改用 per-task NPZ snapshots。
**Source**: `llmdoc/memory/reflections/2026-07-13-ren-formal-tree-scaling-gaps.md`

### Borrow parameters, not algorithm labels
**Rule**: 复用论文的变量范围和扫描流程时，不得自动继承论文中程序的算法身份或理论指数。
**Why**: 当前 Tree TTNS/TTNO local kernel 与 Ren.J.2022 的 MPS TD-DMRG 和 Heidelberg propagation step 不是同一计算对象。
**Source**: `llmdoc/memory/archive/2026-07-13/2026-07-10-ren-style-three-variable-scaling.md`, `llmdoc/memory/reflections/2026-07-13-ren-formal-tree-scaling-gaps.md`
