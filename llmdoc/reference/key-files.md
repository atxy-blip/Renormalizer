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

- `benchmarks/benchmark_adaptive_operator_env.py`
  - `SOPOneSiteEffective`：one-site branch environment，可选 operator signature cache。
  - `SOPMCTDHSweepEnvironment`：strict per-term directed-edge state environment。
  - `_run_point()`：运行选定方法并拆分 env/apply/total timing。

- `benchmarks/ren_formal_manifest.py`
  - 定义 Ren-style Tree benchmark 的 `N_site/M_s/d` 参数和 216 个 array tasks。

- `benchmarks/run_ren_formal_point.py`
  - 运行一个 manifest task，原子保存 JSON-backed compressed NPZ。

- `benchmarks/scripts/curie_cpu_ren_formal_array.sbatch`
  - Curie CPU 正式三变量 array job wrapper。

- `benchmarks/plot_operator_env_scaling.py`
  - 聚合 raw rows，绘制三方法三 panel PDF；固定参考线不进入 legend。

- `renormalizer/tn/tests/test_adaptive_operator_env_benchmark.py`
  - strict message cache、方法选择和 benchmark 字段测试。

- `renormalizer/tn/tests/test_operator_env_scaling_plot.py`
  - 三 panel 聚合、reference curve 和 PDF plotter 测试。

- `renormalizer/tn/tests/test_ren_formal_benchmark.py`
  - formal manifest、snapshot 原子落盘和 task runner 测试。

- `benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`
  - 历史 full-state flat SOP vs TTNO apply benchmark。

- `renormalizer/tn/tests/test_sop_baseline.py`
  - SOP 与 TTNO dense/apply/expectation 一致性测试。

- `renormalizer/tn/tests/test_sop_baseline_dense.py`
  - dense exact operator 对照。

- `renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py`
  - Hubbard junction reduced case 对照。
