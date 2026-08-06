# TTNO Action-Layer Narrative Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Li.W.2024 operator-scaling 结果重新定位为“TTNO 局部作用步骤（local action kernel）本身高度优化”的窄口径叙事：正文图只对 `modes` panel 报 scaling 指数（N_b^3/N_b^2/N_b），`state_bond` 与 `primitive_basis` 以参数稳健性呈现（不报指数、不画幂次参考线、标注 topology switch）；指数与幂次参考线完整保留在 SI 图和 SI fits 中；新增 paired/contracted 叶子因子化说明文档；所有再生成与验证通过 Slurm 提交。

**Architecture:** 不改动任何 benchmark 计算代码与已有 189 个 snapshots；只重构绘图/拟合契约（`benchmarks/plot_li2024_operator_scaling.py`）使其支持 `main`/`si` 两套输出，同步测试，用 Slurm finalizer 从 snapshots 重新生成两套 artifacts，并更新 llmdoc 与设计 spec 中的科学表述。

**Tech Stack:** Python 3.9（conda env `reno-3.9`）、NumPy、Matplotlib、pytest、Slurm（CPU 分区）、Renormalizer benchmark 基础设施、llmdoc。

---

## 科学契约（先读，再动手）

这是老师确认后的口径，所有任务必须围绕它展开：

1. **窄口径、共存式定位**：业界标准是 Heidelberg MCTDH package，但我们不做 head-to-head 对比。论文只证明一件事——在相同 tree、相同 symbolic Hamiltonian、相同 local action 下，TTNO 的局部作用步骤实现得高度优化；SOP 只作为内部参考基线。不写“MCTDH 比 TTNO 慢”这类对抗式表述。
2. **唯一主 scaling 变量是 N_b（modes）**：物理系统大小 = 声子 mode 数。正文主结论只来自 `modes` panel：all-node local action wall time 约 `N_b^3 / N_b^2 / N_b`（`sop_no_env` / `sop_mctdh_like_state_env` / `ttno_with_env`）。
3. **正文与 SI 分工**：
   - 正文三 panel 图：`modes` 保留 `N_b^3/N_b^2/N_b` 幂次参考线；`state_bond` 与 `primitive_basis` 只作参数稳健性检查（不报指数、不画幂次参考线），并标注 adaptive topology switch（d > M_s：paired ↔ contracted）。
   - SI：保留全部 panel 的 largest-four fits 与幂次参考线（M_s 的 M_s^4、大 d 的常数），供审稿人复核。这些是有效 wall-time 指数，不是渐近 FLOP 指数；isolated full-rank internal contraction 的 FLOP 仍是精确 M_s^4。
4. **不做完整 TDVP benchmark**：这是刻意边界，不是缺口。作用步骤已经是完整传播中被反复调用的核心；kernel 更优后，更复杂的后续机制只会更慢，不会逆转结论。
5. **不扩大 M_s 区间、不做 M_s 时间占比/throughput 分解**：再扩大单点就要上万秒，性价比太低；M_s 指数保留在 SI，但不作为正文论证，也不需要额外解释实验。
6. **paired/contracted 单独成文**：解释两种叶子因子化、d^4 vs d^2 来源、`d > M_s` 切换规则、active-node 数翻倍造成的跳变，以及“大 d 近常数”的正确读法。
7. **不重跑 benchmark**：189/189 snapshots 是最终数据源，只重新聚合、重新出图、重新出 fits。
8. **Slurm 执行**：artifact 再生成与最终测试验证都通过 sbatch 提交到 CPU 分区（finalizer 复用 `curie_cpu_li2024_formal_finalize.sbatch`；测试验证使用新建的 `curie_cpu_operator_scaling_validation.sbatch`），不在登录节点直接跑正式任务。TDD 迭代中的本地 pytest 仍允许。

## 文件结构

- `benchmarks/plot_li2024_operator_scaling.py`：绘图与拟合契约，支持 `main`/`si` 两种 figure mode（唯一实质代码改动）。
- `renormalizer/tn/tests/test_li2024_formal_benchmark.py`：契约测试（TDD 先行）。
- `benchmarks/scripts/curie_cpu_operator_scaling_validation.sbatch`：新建 Slurm 验证脚本。
- `benchmarks/results/operator_env_scaling/final/`：main + SI 两套 artifacts：
  - `li2024_spin_boson_20260713_{fits,summary}.csv`
  - `li2024_spin_boson_20260713_scaling_three_panel.{pdf,png}`
  - `li2024_spin_boson_20260713_si_fits.csv`
  - `li2024_spin_boson_20260713_si_scaling_three_panel.{pdf,png}`
- `llmdoc/architecture/paired-vs-contracted-leaves.md`：新增，说明两种叶子布局。
- `llmdoc/index.md`、`llmdoc/overview/scaling-benchmark-status.md`、`llmdoc/must/ttns-sop-task-context.md`、`llmdoc/memory/doc-gaps.md`、`llmdoc/reference/key-files.md`、`llmdoc/guides/sop-environment-benchmark-flow.md`：叙事与缺口同步。
- `docs/superpowers/specs/2026-07-13-li2024-spin-boson-operator-scaling-design.md`：加修订注记。

---

### Task 1: 重构绘图/拟合契约为 main + SI 两套输出（TDD）

**Files:**
- Modify: `benchmarks/plot_li2024_operator_scaling.py`
- Modify: `renormalizer/tn/tests/test_li2024_formal_benchmark.py`

- [ ] **Step 1: 先写失败测试**

把 `renormalizer/tn/tests/test_li2024_formal_benchmark.py` 的 import 改为：

```python
from benchmarks.plot_li2024_operator_scaling import (
    FIT_PANELS_MAIN,
    FIT_PANELS_SI,
    MODE_REFERENCE_POWERS,
    PARAMETER_REFERENCE_POWERS,
    TOPO_SWITCH_X,
    generate,
    summarize,
)
```

把 `test_li2024_plot_guides_match_binary_tree_mathematics` 整个替换为：

```python
def test_li2024_main_si_plot_contract():
    assert MODE_REFERENCE_POWERS == {
        "sop_no_env": 3.0,
        "sop_mctdh_like_state_env": 2.0,
        "ttno_with_env": 1.0,
    }
    assert PARAMETER_REFERENCE_POWERS == {
        "state_bond": {method: 4.0 for method in FORMAL_METHODS},
        "primitive_basis": {method: 0.0 for method in FORMAL_METHODS},
    }
    assert [panel.name for panel in FIT_PANELS_MAIN] == ["modes"]
    assert [panel.name for panel in FIT_PANELS_SI] == ["modes", "state_bond", "primitive_basis"]
    assert TOPO_SWITCH_X == {
        "state_bond": 10.0,
        "primitive_basis": 20.0,
    }
```

在测试文件 import 区之后新增辅助函数：

```python
def _synthetic_row(panel, method, value, time_scale, repeat_id=0):
    n_modes = value if panel == "modes" else 16
    state_bond = value if panel == "state_bond" else 20
    primitive_basis = value if panel == "primitive_basis" else 10
    contracted = primitive_basis > state_bond
    return {
        "status": "ok",
        "case_name": "li2024_spin_boson",
        "quantity": "local_effective_1site_apply_all_nodes",
        "panel": panel,
        "method": method,
        "n_modes": n_modes,
        "target_state_bond": state_bond,
        "primitive_basis_dim": primitive_basis,
        "contract_primitive": contracted,
        "state_max_bond": state_bond,
        "phonon_tree_layout": "primitive_contracted" if contracted else "paired_no_contraction",
        "n_active_nodes": 32 if contracted else 16,
        "n_sop_terms": 1 + 3 * n_modes,
        "ttno_max_bond": 3,
        "state_tensor_elements": 1000,
        "operator_tensor_elements": 2000,
        "repeat_id": repeat_id,
        "time_total_sec": float(value) * time_scale,
        "time_env_build_sec": 0.25 * float(value) * time_scale,
        "time_apply_sec": 0.75 * float(value) * time_scale,
        "relative_error_vs_ttno": 0.0,
    }
```

在 `test_li2024_plot_writes_paired_formal_outputs` 中 `assert fits` 之后加一行：

```python
    assert {f["panel"] for f in fits} == {"modes"}
```

新增 SI 输出测试：

```python
def test_li2024_si_outputs_keep_parameter_exponents(tmp_path):
    rows = []
    for panel, values in (
        ("modes", (4, 8)),
        ("state_bond", (4, 8)),
        ("primitive_basis", (4, 8)),
    ):
        for method in FORMAL_METHODS:
            for value in values:
                rows.append(_synthetic_row(panel, method, value, 1.0))
    summary, fits, pdf, png = generate(rows, tmp_path / "li2024", figure_mode="si")
    assert {f["panel"] for f in fits} == {"modes", "state_bond", "primitive_basis"}
    assert pdf.name == "li2024_si_scaling_three_panel.pdf"
    assert png.name == "li2024_si_scaling_three_panel.png"
```

新增稳健性测试：

```python
def test_li2024_robustness_panels_keep_method_ranking():
    rows = []
    for panel in ("state_bond", "primitive_basis"):
        for value in (4, 16, 100):
            for method, scale in (
                ("sop_no_env", 100.0),
                ("sop_mctdh_like_state_env", 10.0),
                ("ttno_with_env", 1.0),
            ):
                rows.append(_synthetic_row(panel, method, value, scale))
    summary = summarize(rows)
    by_point = {}
    for row in summary:
        key = (row["panel"], row["target_state_bond"], row["primitive_basis_dim"])
        by_point.setdefault(key, {})[row["method"]] = row["time_total_mean_sec"]
    assert len(by_point) == 6
    for times in by_point.values():
        assert times["ttno_with_env"] < times["sop_mctdh_like_state_env"] < times["sop_no_env"]
```

把 `test_li2024_finalizer_reports_both_figure_paths` 中的断言改为同时检查 main 和 SI：

```python
    output = capsys.readouterr().out
    assert "li2024_scaling_three_panel.pdf" in output
    assert "li2024_si_scaling_three_panel.pdf" in output
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
export RENO_GPU=cpu RENO_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/reno-mpl-check
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_li2024_formal_benchmark.py -q
```

Expected: FAIL with `ImportError: cannot import name 'FIT_PANELS_MAIN'`（新名字尚未实现）。

- [ ] **Step 3: 实现最小改动**

修改 `benchmarks/plot_li2024_operator_scaling.py`：

把模块 docstring 改为：

```python
"""Plot the Li.W.2024 spin--boson setup for the three operator kernels.

Figure modes (2026-08-06):
- main: only the modes panel reports scaling exponents (N_b^3 / N_b^2 / N_b);
  the state-bond and primitive-basis panels are parameter robustness checks
  (no exponent fits, no power-law guides) with the adaptive topology switch
  (paired <-> contracted) marked by a vertical line.
- si: all three panels keep their largest-four fits and power-law guides
  (M_s^4 for state bond, constant for large d) for reviewers.
"""
```

把 `REFERENCE_POWERS = {...}` 整个替换为：

```python
MODE_REFERENCE_POWERS = {
    "sop_no_env": 3.0,
    "sop_mctdh_like_state_env": 2.0,
    "ttno_with_env": 1.0,
}

PARAMETER_REFERENCE_POWERS = {
    "state_bond": {method: 4.0 for method in FORMAL_METHODS},
    "primitive_basis": {method: 0.0 for method in FORMAL_METHODS},
}
```

把 `PANELS = (...)` 替换为（标题保持中性，正文/SI 共用）：

```python
PANELS = (
    Panel("modes", "n_modes", r"Number of modes, $N_b$", "Mode number", "N_b"),
    Panel("state_bond", "target_state_bond", r"State bond dimension, $M_s$", "State bond", "M_s"),
    Panel("primitive_basis", "primitive_basis_dim", r"Primitive basis, $d$", "Primitive basis", "d"),
)
FIT_PANELS_MAIN = (PANELS[0],)
FIT_PANELS_SI = PANELS
TOPO_SWITCH_X = {
    "state_bond": 10.0,
    "primitive_basis": 20.0,
}
```

把 `compute_fits(summary)` 改为：

```python
def compute_fits(summary, panels=FIT_PANELS_MAIN):
    fits = []
    for panel in panels:
        for method in FORMAL_METHODS:
            points = sorted(
                (
                    row for row in summary
                    if row["panel"] == panel.name
                    and row["method"] == method
                    and float(row["time_total_mean_sec"]) > 0
                ),
                key=lambda row: float(row[panel.x_field]),
            )
            for window, selected in (("all", points), ("largest_four", points[-4:])):
                if len(selected) < 2:
                    continue
                alpha, intercept, r2 = _fit(selected, panel.x_field)
                fits.append({
                    "panel": panel.name,
                    "method": method,
                    "x_axis": panel.x_field,
                    "fit_window": window,
                    "alpha": alpha,
                    "intercept_logC": intercept,
                    "r2": r2,
                    "n_points": len(selected),
                    "x_min": float(selected[0][panel.x_field]),
                    "x_max": float(selected[-1][panel.x_field]),
                })
    return fits
```

把 `plot(summary, output_prefix)` 改为接受 figure mode 和显式 PDF 路径：

```python
def plot(summary, pdf_path, figure_mode="main"):
    if figure_mode not in ("main", "si"):
        raise ValueError(f"unsupported figure_mode: {figure_mode!r}")
    with nature_style():
        fig, axes = plt.subplots(1, 3, figsize=(10.5, 2.8), sharey=True)
        fig.subplots_adjust(
            left=0.075,
            right=0.985,
            bottom=0.20,
            top=0.90,
            wspace=0.10,
        )
        for panel_index, (ax, panel) in enumerate(zip(axes, PANELS)):
            all_x = []
            for method in FORMAL_METHODS:
                points = sorted(
                    (
                        row for row in summary
                        if row["panel"] == panel.name and row["method"] == method
                    ),
                    key=lambda row: float(row[panel.x_field]),
                )
                if not points:
                    continue
                x = np.asarray([float(row[panel.x_field]) for row in points])
                y = np.asarray([float(row["time_total_mean_sec"]) for row in points])
                yerr = np.asarray([float(row["time_total_std_sec"]) for row in points])
                style = METHOD_STYLES[method]
                color = style["color"]
                ax.errorbar(
                    x,
                    y,
                    yerr=yerr,
                    capsize=2,
                    label=METHOD_LABELS[method],
                    **style,
                )

                if panel.name == "modes":
                    power = MODE_REFERENCE_POWERS[method]
                    ref_x = x
                    ref_y = y[-1] * (ref_x / ref_x[-1]) ** power
                    ax.plot(ref_x, ref_y, linestyle="--", color=color, alpha=0.7)
                    ax.text(
                        0.97,
                        ref_y[-1],
                        _guide_label(panel.symbol, power),
                        transform=ax.get_yaxis_transform(),
                        color=color,
                        ha="right",
                        va="center",
                        clip_on=True,
                    )
                elif figure_mode == "si":
                    power = PARAMETER_REFERENCE_POWERS[panel.name][method]
                    ref_x = x[len(x) // 2 :]
                    ref_y = y[-1] * (ref_x / ref_x[-1]) ** power
                    ax.plot(ref_x, ref_y, linestyle="--", color=color, alpha=0.7)
                    ax.text(
                        0.97,
                        ref_y[-1],
                        _guide_label(panel.symbol, power),
                        transform=ax.get_yaxis_transform(),
                        color=color,
                        ha="right",
                        va="center",
                        clip_on=True,
                    )
                all_x.extend(x.tolist())

            if figure_mode == "main":
                switch_x = TOPO_SWITCH_X.get(panel.name)
                if switch_x is not None:
                    ax.axvline(switch_x, color="0.45", linestyle=":", linewidth=1.0)
                    ax.text(
                        switch_x,
                        0.5,
                        "contracted | paired" if panel.name == "state_bond" else "paired | contracted",
                        transform=ax.get_yaxis_transform(),
                        rotation=90,
                        ha="right",
                        va="center",
                        fontsize=6,
                        color="0.35",
                    )

            ax.set_xscale("log", base=2)
            ax.set_yscale("log")
            if all_x:
                ax.set_xticks(sorted(set(all_x)))
                ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
            ax.set_xlabel(panel.xlabel)
            label_panel(ax, chr(ord("a") + panel_index), panel.title)
            finish_axis(ax)

        axes[0].set_ylabel("All-node local-action wall time (s)")
        axes[0].legend(loc="upper left", frameon=False)
        pdf, png = save_pdf_png(fig, pdf_path)
        plt.close(fig)
    return pdf, png
```

把 `generate(rows, output_prefix)` 改为：

```python
def generate(rows, output_prefix, figure_mode="main"):
    if figure_mode not in ("main", "si"):
        raise ValueError(f"unsupported figure_mode: {figure_mode!r}")
    ok_rows = [row for row in rows if row.get("status") == "ok"]
    cases = {row.get("case_name") for row in ok_rows}
    quantities = {row.get("quantity") for row in ok_rows}
    if cases != {"li2024_spin_boson"}:
        raise ValueError(f"expected only li2024_spin_boson rows, found {sorted(cases)}")
    if quantities != {"local_effective_1site_apply_all_nodes"}:
        raise ValueError(f"expected all-node local actions, found {sorted(quantities)}")
    summary = summarize(rows)
    panels = FIT_PANELS_MAIN if figure_mode == "main" else FIT_PANELS_SI
    fits = compute_fits(summary, panels=panels)
    fits_path = output_prefix.with_name(
        output_prefix.name + ("_fits.csv" if figure_mode == "main" else "_si_fits.csv")
    )
    _write_csv(fits_path, fits)
    if figure_mode == "main":
        _write_csv(output_prefix.with_name(output_prefix.name + "_summary.csv"), summary)
    pdf_path = output_prefix.with_name(
        output_prefix.name
        + ("_scaling_three_panel.pdf" if figure_mode == "main" else "_si_scaling_three_panel.pdf")
    )
    pdf, png = plot(summary, pdf_path, figure_mode=figure_mode)
    return summary, fits, pdf, png
```

修改 `benchmarks/finalize_li2024_formal.py` 的 `main()`：

```python
    summary, fits, pdf, png = generate(rows, args.output_prefix, figure_mode="main")
    summary, si_fits, si_pdf, si_png = generate(rows, args.output_prefix, figure_mode="si")
    print(
        f"Collected {len(rows)}/{len(expected)} snapshots; "
        f"wrote {len(summary)} summary rows, {len(fits)} main fits, {len(si_fits)} SI fits, "
        f"and figures {pdf}, {png}, {si_pdf}, {si_png}"
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
export RENO_GPU=cpu RENO_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/reno-mpl-check
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_li2024_formal_benchmark.py -q
```

Expected: PASS（含新增的 3 个测试）。

- [ ] **Step 5: 跑相关本地测试集（TDD 迭代，不替代 Slurm 验证）**

Run:

```bash
export RENO_GPU=cpu RENO_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/reno-mpl-check
conda run -n reno-3.9 python -m pytest renormalizer/tn/tests/test_sop_baseline.py renormalizer/tn/tests/test_sop_baseline_dense.py renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py renormalizer/tn/tests/test_li2024_formal_benchmark.py renormalizer/tn/tests/test_contraction_scaling_diagnostics.py -q
```

Expected: 30 passed（原 28 个 + 新增 SI 测试 + 新增稳健性测试）。

- [ ] **Step 6: Commit**

```bash
git add benchmarks/plot_li2024_operator_scaling.py benchmarks/finalize_li2024_formal.py renormalizer/tn/tests/test_li2024_formal_benchmark.py
git commit -m "feat: split Li2024 plot contract into main and SI outputs"
```

---

### Task 2: 用 Slurm finalizer 重新生成 main + SI artifacts

**Files:**
- Regenerate (via Slurm): `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_fits.csv`
- Regenerate: `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_summary.csv`
- Regenerate: `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.{pdf,png}`
- Regenerate: `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_fits.csv`
- Regenerate: `benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_scaling_three_panel.{pdf,png}`

- [ ] **Step 1: 提交 finalizer Slurm 作业**

Run:

```bash
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```

Expected: 输出 `Submitted batch job <jobid>`。不要在登录节点直接运行 finalizer。

- [ ] **Step 2: 等待并确认作业状态**

Run:

```bash
squeue -u "$USER" --name li2024_op_plot
sacct -j <jobid> --format=JobID,JobName,State,ExitCode --noheader
```

Expected: 作业进入 `COMPLETED`，`ExitCode=0:0`。若失败，读 `benchmarks/results/operator_env_scaling/li2024_formal/logs/finalize_<jobid>.log`。

- [ ] **Step 3: 验证 main/SI 输出**

Run:

```bash
cut -d, -f1 benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_fits.csv | sort -u
cut -d, -f1 benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_fits.csv | sort -u
cat benchmarks/results/operator_env_scaling/li2024_formal/missing_or_error_tasks.json
ls -l benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713*scaling_three_panel*
```

Expected:
- main fits 第一列只有 `panel` 和 `modes`（6 行 fits）；
- SI fits 第一列为 `panel`、`modes`、`state_bond`、`primitive_basis`（18 行 fits）；
- missing json 仍为 `"missing_or_error_task_ids": []`；
- main 与 SI 的 PDF/PNG 都存在。

- [ ] **Step 4: 目检两张图**

打开 main PNG：`li2024_spin_boson_20260713_scaling_three_panel.png`

Expected:
- modes panel 有 `N_b^3/N_b^2/N_b` 三条虚线；
- state_bond panel 在 `M_s=10` 有竖直虚线，标注 `contracted | paired`，无幂次参考线；
- primitive_basis panel 在 `d=20` 有竖直虚线，标注 `paired | contracted`，无幂次参考线；
- 相对排名在每个参数点保持 TTNO 最快、strict state env 次之、no env 最慢。

打开 SI PNG：`li2024_spin_boson_20260713_si_scaling_three_panel.png`

Expected:
- 三个 panel 均保留幂次参考线（modes: 3/2/1；state_bond: M_s^4；primitive_basis: 常数）；
- 不画 topology switch 线（SI 保持经典指数图）。

- [ ] **Step 5: Commit**

```bash
git add benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_fits.csv benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_summary.csv benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_fits.csv benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_scaling_three_panel.pdf benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_si_scaling_three_panel.png
git commit -m "results: regenerate Li2024 main and SI artifacts"
```

---

### Task 3: 新增 paired/contracted 叶子因子化文档

**Files:**
- Create: `llmdoc/architecture/paired-vs-contracted-leaves.md`
- Modify: `llmdoc/index.md`

- [ ] **Step 1: 新增架构文档**

创建 `llmdoc/architecture/paired-vs-contracted-leaves.md`，内容如下：

````markdown
# Paired vs Contracted 声子叶因子化

## 目的

解释 Li.W.2024 spin-boson benchmark 中两种声子叶因子化的结构、存储/FLOP
差异、自适应切换规则，以及切换造成的全模型 wall-time 跳变。避免把
“拓扑切换”误读为算法本身的复杂度变化。

## 两种布局

`contract_primitive = (d > M_s)` 决定 phonon tree 布局：

- `paired_no_contraction`（d <= M_s）
  - 每个 leaf 合并 2 个 primitive modes。
  - state leaf tensor shape：`(M_s, d, d)`。
  - TTNO leaf tensor shape：`(O, d, d, d, d)`，即 4 个 physical operator axes。
  - isolated leaf optimized FLOPs：`F(d) = 160 d^4 + 3200 d^2`；
    全树 TTNO 元素数：`N_TTNO(d) = 32 d^4 + 1354`。
- `primitive_contracted`（d > M_s）
  - 每个 leaf 只含 1 个 primitive mode。
  - state leaf tensor shape：`(M_s, d)`。
  - TTNO leaf tensor shape：`(O, d, d)`，即 2 个 physical operator axes。
  - isolated leaf optimized FLOPs：`F(d) = 160 d^2 + 3200 d`；
    全树 TTNO 元素数：`N_TTNO(d) = 48 d^2 + 1642`。

公式来源：`benchmarks/results/operator_env_scaling/contraction_diagnostics/analysis.md`
（shape-only optimized FLOPs 与 tensor storage 精确匹配，最大绝对偏差为零）。

## 为什么会有 d^4

paired leaf 的稠密 TTNO 张量把 d×d 的 primitive 乘积空间映射到自身，因此
元素数为 `(d^2) * (d^2) = d^4`。这不是 TTNO 表示的一般性质，而是“一个 leaf
合并两个 primitive modes”的 grouping 选择。primitive contraction 恢复
one-mode leaf 后，operator 张量回到 `(O, d, d)`，渐近元素数为 `d^2`。

## 切换点的全模型影响

16 个 modes 时：

- paired：8 个 phonon leaves，`n_active_nodes = 16`；
- contracted：16 个 phonon leaves，`n_active_nodes = 32`。

leaf 个数翻倍，同时每个 leaf 的稠密成本从 d^4 降到 d^2。两个效应叠加，
全模型 wall time 在切换点出现非单调跳变：

- `state_bond` panel（固定 d=10）：M_s=8（contracted）→ M_s=16（paired）时，
  `sop_no_env` 从约 32.5 s 降到约 8.0 s；
- `primitive_basis` panel（固定 M_s=20）：d=16（paired）→ d=32（contracted）时，
  `sop_no_env` 从约 8.4 s 跳到约 35.5 s。

TTNO 路径同样受 active-node 数影响，但绝对幅度小得多。

## 正文与 SI 的分工

- 正文三 panel 图：`modes` 保留 `N_b^3/N_b^2/N_b` 参考线；`state_bond` 与
  `primitive_basis` 只作参数稳健性检查（不报指数、不画幂次参考线），并标注
  切换线。
- SI 图：保留全部 panel 的 largest-four fits 与幂次参考线（M_s^4、常数），
  供审稿人复核；这些是有效 wall-time 指数，不是渐近 FLOP 指数。

## 正确解读

- 大 d 区间的“近常数”是“切换到 contracted layout 之后、固定 body-tree
  工作占主导”的结果，不是 leaf 计算本身 O(1)；isolated leaf 的 FLOPs
  和 TTNO storage 仍渐近 d^2。
- 系统大小 scaling 的唯一主结论来自 `modes` panel（固定 M_s=20、d=10、
  全 paired）：`N_b^3 / N_b^2 / N_b`（`sop_no_env` / `sop_mctdh_like_state_env` /
  `ttno_with_env`）。
- 图件中两个参数 panel 必须标注切换线，并在正文用一句话说明跳变来自
  拓扑切换，而不是数值错误或算法复杂度变化。
````

- [ ] **Step 2: 在 llmdoc 索引中加入链接**

在 `llmdoc/index.md` 的“架构说明”列表中追加一行：

```markdown
- `llmdoc/architecture/paired-vs-contracted-leaves.md`：两种声子叶因子化的结构、d^4/d^2 来源、自适应切换规则与全模型跳变解读。
```

- [ ] **Step 3: Commit**

```bash
git add llmdoc/architecture/paired-vs-contracted-leaves.md llmdoc/index.md
git commit -m "docs: explain paired vs contracted leaf factorizations"
```

---

### Task 4: 同步叙事文档与缺口清单（含正文/SI 分工与 Slurm 流程）

**Files:**
- Modify: `llmdoc/overview/scaling-benchmark-status.md`
- Modify: `llmdoc/must/ttns-sop-task-context.md`
- Modify: `llmdoc/memory/doc-gaps.md`
- Modify: `llmdoc/reference/key-files.md`
- Modify: `llmdoc/guides/sop-environment-benchmark-flow.md`

- [ ] **Step 1: 更新 scaling-benchmark-status.md 的 Li.W.2024 小节**

把 `## Li.W.2024 spin-boson rerun` 小节中从 `largest-four-point wall-time fit：` 起到该小节结束的内容替换为：

```markdown
### 正式解释口径（2026-08-06）

正文图 `li2024_spin_boson_20260713_scaling_three_panel.{pdf,png}`：

- `modes` panel 是唯一报 scaling 指数的面板（largest-four fit）：

| 方法 | N_b exponent |
| --- | ---: |
| `sop_no_env` | 3.109 |
| `sop_mctdh_like_state_env` | 2.035 |
| `ttno_with_env` | 0.916 |

对应 `N_b^3 / N_b^2 / N_b` 的 state/operator reuse 结构。

- `state_bond` 与 `primitive_basis` panel 只作参数稳健性检查：不报指数、
  不画幂次参考线；三条方法相对排名在每个参数点稳定（TTNO 最快，strict
  state env 次之，no env 最慢）；两个 panel 均标注 adaptive topology switch
  （d > M_s：paired ↔ contracted），跳变来自 leaf 数翻倍与 d^4 → d^2 切换，
  详见 `llmdoc/architecture/paired-vs-contracted-leaves.md`。

指数与幂次参考线完整保留在 SI：

```text
li2024_spin_boson_20260713_si_scaling_three_panel.{pdf,png}
li2024_spin_boson_20260713_si_fits.csv
```

SI 图中 M_s panel 保留 M_s^4 参考线，大 d panel 保留常数参考线。它们是有效
wall-time 指数与参考线，不是渐近 FLOP 指数；isolated full-rank internal
contraction 的 FLOP 仍为精确 M_s^4（见 contraction diagnostics）。

刻意边界：

- 本 benchmark 只测量 `local_effective_1site_apply_all_nodes` kernel，不做
  完整 TDVP/传播 step 计时；这是有意的窄口径对比，不是缺口。
- 不扩大 M_s 区间；不做 M_s 时间占比/throughput 分解。

### 再生成方式

所有 main/SI artifacts 由现有 189 个 snapshots 经 Slurm finalizer 生成，
不重跑 benchmark：

```bash
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```
```

- [ ] **Step 2: 更新 ttns-sop-task-context.md 的正式 rerun 小节**

把 `## 当前正式 Li.W.2024 spin-boson rerun` 小节中从 `largest-four-point wall-time fit：` 起到该小节结束的内容替换为：

```markdown
正式解释口径（2026-08-06）：

- 只对 `modes` panel 报 scaling 指数（largest-four fit）：N_b 约为
  3.11 / 2.04 / 0.92（`sop_no_env` / `sop_mctdh_like_state_env` /
  `ttno_with_env`），对应 `N_b^3 / N_b^2 / N_b`。
- `state_bond` 与 `primitive_basis` panel 在正文只做参数稳健性检查：不报
  指数、不画幂次参考线；相对排名在每个点上稳定。
- M_s^4 与常数参考线、M_s/d 的 largest-four fits 保留在 SI
  （`*_si_fits.csv`、`*_si_scaling_three_panel.*`）。
- adaptive topology switch（d > M_s：paired ↔ contracted）会造成全模型
  wall-time 跳变，正文图必须标注；见
  `llmdoc/architecture/paired-vs-contracted-leaves.md`。
- 不做完整 TDVP/传播 step 计时，这是刻意边界，不是缺口。
```

- [ ] **Step 3: 更新 doc-gaps.md**

把 `llmdoc/memory/doc-gaps.md` 整个文件替换为：

```markdown
# 文档缺口

当前已初始化与 SOP/TTNO environment 任务直接相关的 llmdoc。

仍待处理：

- 如果后续修改 TDVP sweep 或 local effective Hamiltonian API，补充调用链图。
- legacy Hubbard-junction formal array 仍只有 204/216 个快照。闭合条件：明确
  标记为 superseded partial archive，或补齐 no-env `N=300` 和全部 `M_s=300`
  repeats；不要与 189/189 Li.W.2024 spin-boson final result 混用。

已决定/已闭合（2026-08-06）：

- 不做完整 TDVP/传播 step benchmark。`local_effective_1site_apply_all_nodes`
  与完整 step 的时间组成差异是刻意边界，不是缺口。
- 不扩大 full-rank full-workflow 区间，不做 M_s 时间占比/throughput 分解。
- Li.W.2024 的 M_s/d 指数与幂次参考线保留在 SI；正文只报 modes panel 指数。
  isolated full-rank internal-node `M_s^4` FLOP 结论保留在 contraction
  diagnostics，SI 中的 M_s^4 参考线是有效 wall-time 参考，不是 FLOP 渐近指数。
- paired vs contracted topology switch 已由
  `llmdoc/architecture/paired-vs-contracted-leaves.md` 专门说明。

已补充：

- `llmdoc/architecture/ttns-ttno-environment.md` 已记录 `SOPOneSiteEffective`、`SOPMCTDHSweepEnvironment`、cache key 与 root/all-nodes timing object 区别。
- `llmdoc/guides/sop-environment-benchmark-flow.md` 已记录四类 benchmark label 和 strict MCTDH-like all-nodes sanity 结果。
- `llmdoc/architecture/primitive-contraction-scaling.md` 已用 actual tensor shape、
  exact optimized FLOPs、TTNO element count 和 peak memory 解释 paired leaf
  `d^4`；primitive contraction 恢复 one-mode leaf 的渐近 `d^2` storage/FLOPs。
- `llmdoc/overview/scaling-benchmark-status.md` 已记录 144/144 diagnostics、
  189/189 Li.W.2024 rerun、正文/SI 分工和 2026-08-06 正式解释口径。
- `llmdoc/architecture/paired-vs-contracted-leaves.md` 已说明两种叶子布局与
  拓扑切换跳变。
```

- [ ] **Step 4: 更新 key-files.md 的 plot 模块描述**

把 `llmdoc/reference/key-files.md` 中这两行：

```markdown
- `benchmarks/plot_li2024_operator_scaling.py`
  - 聚合 Li.W.2024 repeats，拟合 all/largest-four 窗口，绘制 Nature-style
    three-panel PDF/PNG。
```

替换为：

```markdown
- `benchmarks/plot_li2024_operator_scaling.py`
  - 聚合 Li.W.2024 repeats；支持 `figure_mode="main"/"si"`：main 只对 modes
    panel 拟合 largest-four 指数并绘制稳健性面板（标注 topology switch）；
    si 保留全部 panel 的指数与幂次参考线。finalizer 同时生成两套 PDF/PNG
    与 fits。
```

- [ ] **Step 5: 更新 benchmark flow 指南 Step 8**

在 `llmdoc/guides/sop-environment-benchmark-flow.md` 的 Step 8 中，
“注意：primitive contraction 会改变 tree topology ...” 段落后追加：

```markdown
正文/SI 分工（2026-08-06）：

- 正文三 panel 图只对 `modes` 报 `N_b^3/N_b^2/N_b`；`state_bond` 与
  `primitive_basis` 只作稳健性检查（不报指数、不画幂次参考线），并标注
  d > M_s topology switch。
- SI 图保留全部 panel 的 largest-four fits 与幂次参考线（M_s^4、常数），
  供审稿人复核；这些是有效 wall-time 指数，不是渐近 FLOP 指数。
- artifact 再生成用 Slurm finalizer：

```bash
sbatch benchmarks/scripts/curie_cpu_li2024_formal_finalize.sbatch
```

不重跑 189 个 snapshot。
```

- [ ] **Step 6: Commit**

```bash
git add llmdoc/overview/scaling-benchmark-status.md llmdoc/must/ttns-sop-task-context.md llmdoc/memory/doc-gaps.md llmdoc/reference/key-files.md llmdoc/guides/sop-environment-benchmark-flow.md
git commit -m "docs: reframe Li2024 results with main/SI and Slurm workflow"
```

---

### Task 5: 更新设计 spec 修订注记

**Files:**
- Modify: `docs/superpowers/specs/2026-07-13-li2024-spin-boson-operator-scaling-design.md`

- [ ] **Step 1: 在 spec 顶部加修订注记**

在 `docs/superpowers/specs/2026-07-13-li2024-spin-boson-operator-scaling-design.md`
的标题 `## Goal` 之前插入：

```markdown
> **2026-08-06 修订**：plot contract 已更新——正文图只对 `modes` panel 报
> scaling 指数（`N_b^3/N_b^2/N_b`）；`state_bond` 与 `primitive_basis` panel
> 在正文以参数稳健性呈现（不报指数、不画幂次参考线，标注 topology switch）；
> 全部 panel 的指数与幂次参考线保留在 SI（`*_si_fits.csv`、
> `*_si_scaling_three_panel.*`）。实现见
> `docs/superpowers/plans/2026-08-06-operator-scaling-narrative-refactor.md`。
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-07-13-li2024-spin-boson-operator-scaling-design.md
git commit -m "docs: mark Li2024 plot contract revision"
```

---

### Task 6: 新建 Slurm 验证脚本并提交全量验证

**Files:**
- Create: `benchmarks/scripts/curie_cpu_operator_scaling_validation.sbatch`

- [ ] **Step 1: 新建验证脚本**

创建 `benchmarks/scripts/curie_cpu_operator_scaling_validation.sbatch`：

```bash
#!/bin/bash
#SBATCH --time=0-02:00:00
#SBATCH --job-name=op_scaling_validation
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --partition=CPU
#SBATCH --mem=64GB
#SBATCH --qos=normal
#SBATCH --output=benchmarks/results/slurm_logs/op_scaling_validation_%j.log

set -euo pipefail

source /software/envs/bash.profile
source /software/envs/anaconda3.env
conda activate reno-3.9

export RENO_NUM_THREADS=1
export RENO_GPU=cpu
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

REPO_DIR=${REPO_DIR:-/curie-home/yuxiong/Reno-quantity}
cd "$REPO_DIR"

mkdir -p benchmarks/results/slurm_logs

echo "Job: ${SLURM_JOB_ID:-local} Host: $(hostname)"

python -m py_compile \
    benchmarks/plot_li2024_operator_scaling.py \
    benchmarks/finalize_li2024_formal.py \
    renormalizer/tn/sop_baseline.py

python -m pytest \
    renormalizer/tn/tests/test_sop_baseline.py \
    renormalizer/tn/tests/test_sop_baseline_dense.py \
    renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py \
    renormalizer/tn/tests/test_li2024_formal_benchmark.py \
    renormalizer/tn/tests/test_contraction_scaling_diagnostics.py \
    renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py \
    renormalizer/tn/tests/test_nature_plot_style.py \
    -q

echo "Finished: $(date)"
exit 0
```

- [ ] **Step 2: 提交验证作业**

Run:

```bash
sbatch benchmarks/scripts/curie_cpu_operator_scaling_validation.sbatch
```

Expected: `Submitted batch job <jobid>`。

- [ ] **Step 3: 等待并确认状态与日志**

Run:

```bash
squeue -u "$USER" --name op_scaling_validation
sacct -j <jobid> --format=JobID,JobName,State,ExitCode --noheader
tail -n 20 benchmarks/results/slurm_logs/op_scaling_validation_<jobid>.log
```

Expected: `COMPLETED`、`ExitCode=0:0`，日志末尾 `Finished:` 且 pytest 全 PASS。

- [ ] **Step 4: 检查工作树与 diff**

Run:

```bash
git status --short
git diff --check
```

Expected: 工作树干净（或只有尚未提交的 llmdoc 收尾改动）；`git diff --check` 无输出。

- [ ] **Step 5: 提示老师运行 /llmdoc:update**

llmdoc watermark 目前落后 HEAD 约 25 个 commit，本次又新增/修改了稳定文档。最后向老师报告时主动询问是否现在运行 `/llmdoc:update`（由 recorder 消费 `watermark..HEAD` 净 diff 并推进 watermark）。

