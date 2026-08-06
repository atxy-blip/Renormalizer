# 核心文件索引

## Symbolic operator

- `renormalizer/model/op.py`
  - `Op`：单个 product operator term。
  - `Op.product()`：串接多个 `Op`。
  - `Op.split_elementary()`：按 site/tree-node 局域化 product term。
  - `OpSum`：`list[Op]` 形式的算符和。

- `renormalizer/model/model.py`
  - `Model`：验证 basis 和 ham_terms，建立 `dof_to_siteidx`。

- `renormalizer/model/basis.py`
  - `BasisSet.op_mat()`：局域 symbolic `Op` 到数值矩阵。
  - `BasisSHO`, `BasisHalfSpin`, `BasisMultiElectronVac`, `BasisDummy` 等具体实现。

## TTNS / TTNO

- `renormalizer/tn/treebase.py`
  - `BasisTree`：树形 basis 拓扑。
  - `dof2idx`：dof 到 tree node index 的映射。

- `renormalizer/tn/tree.py`
  - `TTNS`：tree tensor network state。
  - `TTNO`：tree tensor network operator。
  - `TTNO.apply()`：operator tensor 逐 node 作用到 state tensor。
  - `TTNEnviron`：contraction environment tree。

- `renormalizer/tn/symbolic_ttno.py`
  - `construct_symbolic_ttno()`：从 `List[Op]` 构造 symbolic TTNO。
  - `symbolic_mo_to_numeric_mo_general()`：symbolic matrix operator 到数值 TTNO tensor。

- `renormalizer/tn/hop_expr.py`
  - `hop_expr1()`：one-site local effective Hamiltonian。
  - `hop_expr2()`：two-site local effective Hamiltonian。
  - `hop_expr0()`：TDVP zero-site action。

- `renormalizer/tn/time_evolution.py`
  - `evolve_tdvp_vmf()`
  - `evolve_tdvp_ps()`
  - `evolve_tdvp_ps2()`

- `renormalizer/tn/gs.py`
  - `optimize_ttns()`
  - `optimize_2site()`

## SOP baseline

- `renormalizer/tn/sop_baseline.py`
  - `SOPTerm`：一个 flat product term，保存 coefficient 和 node-local ops。
  - `SOPBaselineOperator`：flat SOP operator baseline。
  - `_split_op_by_tree_node()`：用 `BasisTree.dof2idx` 把 `Op` 映射到 tree node。
  - `_apply_term_to_ttns()`：当前 no-env term application。

## Benchmark / tests

- `notebooks/sop_debugging_lab.ipynb`
  - 十项可执行 SOP debugging investigations、breakpoint policy、formal timing
    boundary 和 supervisor-facing recap。

- `llmdoc/guides/sop-linear-learning-checklist.md`
  - 12 个 45 分钟、严格顺序且以实际证据为完成条件的 SOP 学习路线；覆盖 notebook、
    formal manifest-to-figure 数据链、主文/SI 图件和口述自检。

- `benchmarks/sop_debugging_lab.py`
  - `build_lab_case()` 及六个 notebook-friendly helpers；只暴露生产对象的稳定摘要，
    不重实现 benchmark algorithm。

- `benchmarks/nature_plot_style.py`
  - `NATURE_RCPARAMS`：scoped Nature-style typography、inward ticks 与 Type 42
    PDF font policy。
  - `METHOD_STYLES`：`sop_no_env`、strict MCTDH-like SOP、TTNO-with-env 的
    stable color/marker encoding。
  - `nature_style()`、`finish_axis()`、`label_panel()`、`save_pdf_png()`：共享
    rc context、axis treatment、panel label 和 fixed-boundary dual export。

- `benchmarks/benchmark_adaptive_operator_env.py`
  - `SOPOneSiteEffective`：one-site branch environment，可选 operator signature cache。
  - `SOPMCTDHSweepEnvironment`：strict per-term directed-edge state environment。
  - `_run_point()`：运行选定方法并拆分 env/apply/total timing。
  - `build_hubbard_junction_case()`：支持 `phonon_contract_primitive` tree-layout 开关。

- `benchmarks/benchmark_li2024_operator_env.py`
  - 构造 sub-Ohmic spin-boson Hamiltonian 和 adaptive binary tree。
  - `run_li2024_point()`：运行三条 operator path 中的一个 formal point。

- `benchmarks/li2024_formal_manifest.py`
  - 定义 21 个参数点、3 个方法、3 个 repeats，共 189 个 array tasks。
  - `uses_primitive_contraction()`：固定 `d > M_s` topology 规则。

- `benchmarks/run_li2024_formal_point.py`
  - 运行单个 Li formal task，并原子写 JSON-backed NPZ。

- `benchmarks/finalize_li2024_formal.py`
  - 检查 189 个 task IDs，只有全部 `status=ok` 时才生成 final aggregate 和 PDF。

- `benchmarks/plot_li2024_operator_scaling.py`
  - 聚合 Li.W.2024 repeats；支持 `figure_mode="main"/"si"`：main 只对 modes
    panel 拟合 largest-four 指数并绘制稳健性面板（标注 topology switch）；
    si 保留全部 panel 的指数与幂次参考线。finalizer 同时生成两套 PDF/PNG
    与 fits。

- `benchmarks/contraction_scaling_diagnostics.py`
  - 定义 internal-`M_s`、leaf-`d` 和 full-model-`d` 六类 controls。
  - `kernel_path_metrics()`：记录 optimized FLOPs 和 largest intermediate。

- `benchmarks/run_contraction_scaling_diagnostic.py`
  - 运行 isolated dense kernel 或 paired/contracted full-model control。

- `benchmarks/summarize_contraction_scaling_diagnostics.py`
  - 按 repeats 取 median/std，并生成 all/largest-four scaling fits。

- `benchmarks/plot_contraction_scaling_diagnostics.py`
  - 生成 Nature-style `complexity_validation` 和 `model_mechanism` 两组
    two-by-two PDF/PNG diagnostics。

- `benchmarks/ren_formal_manifest.py`
  - 定义 Ren-style Tree benchmark 的 `N_site/M_s/d` 参数和 216 个 array tasks。

- `benchmarks/run_ren_formal_point.py`
  - 运行一个 manifest task，原子保存 JSON-backed compressed NPZ。

- `benchmarks/scripts/curie_cpu_ren_formal_array.sbatch`
  - Curie CPU 正式三变量 array job wrapper。

- `benchmarks/plot_operator_env_scaling.py`
  - 聚合 strict all-node raw rows，绘制三方法 Nature-style three-panel
    PDF/PNG；固定参考线不进入 legend。

- `renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py`
  - strict message cache、方法选择和 benchmark 字段测试。

- `renormalizer/tn/tests/test_operator_env_scaling_plot.py`
  - 三 panel 聚合、reference curve 和 PDF plotter 测试。

- `renormalizer/tn/tests/test_ren_formal_benchmark.py`
  - formal manifest、snapshot 原子落盘和 task runner 测试。

- `renormalizer/tn/tests/test_li2024_formal_benchmark.py`
  - Li formal manifest、adaptive topology、small-point correctness 和 Slurm wrapper 测试。

- `renormalizer/tn/tests/test_contraction_scaling_diagnostics.py`
  - 精确 `M_s^4/d^4/d^2` path metrics、model topology、snapshot 和 summary 测试。

- `renormalizer/tn/tests/test_plot_contraction_scaling_diagnostics.py`
  - numeric sorting、tail fit 和 figure artifact 测试。

- `benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`
  - 历史 full-state flat SOP vs TTNO apply benchmark。

- `renormalizer/tn/tests/test_sop_baseline.py`
  - SOP 与 TTNO dense/apply/expectation 一致性测试。

- `renormalizer/tn/tests/test_sop_baseline_dense.py`
  - dense exact operator 对照。

- `renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py`
  - Hubbard junction reduced case 对照。
