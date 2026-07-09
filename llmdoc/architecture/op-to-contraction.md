# 从 Op 到算符缩并

本文解释 `Op` 类如何表示 Hamiltonian product term，以及它如何进入 TTNO / SOP / contraction 逻辑。

## 1. Op 的数据模型

核心文件：`renormalizer/model/op.py`

`Op` 表示一个 product operator term，例如：

```python
Op("+ Z -", ["L_0", "s^", "R_0"], factor=0.2)
```

关键字段：

- `symbol`：原始字符串，如 `"X"`, `"+ -"`, `"p^2"`。
- `split_symbol`：按空格拆开的 elementary symbols。
- `dofs`：每个 elementary symbol 对应的自由度标签。
- `factor`：整个 product term 的系数。
- `qn_list`：每个 elementary symbol 的量子数变化。
- `qn`：`qn_list` 的总和。

`Op` 设计上主要处理乘法，不直接把加法塞进一个对象。加法返回 `OpSum`，本质是 `list[Op]`。

在 SOP benchmark 里，`n_sop_terms` 数的是 Hamiltonian 被化成：

```text
H = sum_alpha H_alpha
```

之后的 product `Op` 项数。它不是 TTNS site 数，也不是 local basis 维数。一个 `Op` product term 可以跨多个 dof，例如含有 lead hopping 和 fermionic `Z` string；在 TTNS 上它会再被 split 到多个 tree node 的 local operator。

## 2. Op 乘法与 OpSum

`Op.product()` / `Op.__mul__()` 的逻辑是：

- 串接 `symbol`。
- 串接 `dofs`。
- 系数相乘。
- 量子数列表串接。

因此：

```python
Op("X", 0, 0.5) * Op("Y", 1, 0.2)
```

会变成：

```python
Op("X Y", [0, 1], 0.1)
```

`Op.__add__()` 返回 `OpSum([op1, op2])`。`OpSum.simplify()` 可合并相同 symbol/dofs 的 term，并移除小系数项。

## 3. Model 如何建立 dof 到 basis/site 的映射

核心文件：`renormalizer/model/model.py`

`Model(basis, ham_terms)` 做两件重要的事：

- 检查 Hamiltonian term 中的 dof 是否都在 basis 里。
- 建立 `dof_to_siteidx` 和 `dof_to_basis`。

对于 MPS/MPO，这个 site index 是线性 site。

对于 TTNS/TTNO，`BasisTree` 会建立另一套映射：

- `basis.dof2idx[dof]`：dof 属于哪个 tree node。
- `basis.node_list[node_idx].basis_sets`：该 tree node 上有哪些 local basis。

## 4. split_elementary：把 product term 按局域站点分组

`Op.split_elementary(dof_to_siteidx)` 是从 symbolic operator 到 local operator 的关键步骤。

它遍历 `split_symbol`, `dofs`, `qn_list`，按 `dof_to_siteidx` 分组。同一个 site 上的 elementary symbols 保持原顺序，然后用 `Op.product()` 合成一个局域 `Op`。

例子：

```python
op = Op("X Y", [0, 2], 0.5)
op.split_elementary({0: 0, 2: 1})
```

会得到两个 elementary local ops，系数 `0.5` 单独返回。

如果两个 symbol 在同一局域 site 上，则会合并为一个局域 `Op`。

## 5. BasisSet.op_mat：symbolic local Op 到数值矩阵

核心文件：`renormalizer/model/basis.py`

每种局域 basis 负责把局域 `Op` 变成矩阵：

- `BasisSHO.op_mat()`：处理 `x`, `p`, `p^2`, `x^2`, `b^\dagger+b` 等振动算符。
- `BasisHalfSpin.op_mat()`：处理 `X`, `Y`, `Z`, `+`, `-` 等二能级/自旋算符。
- `BasisMultiElectronVac.op_mat()`：处理多电子真空 basis 中的 `a^\dagger`, `a` 等。
- `BasisDummy.op_mat()`：处理 dummy identity。

注意：`op_mat()` 返回的矩阵已经包含该 local `Op` 的 factor。

## 6. Op 到 TTNO

核心文件：

- `renormalizer/tn/tree.py`
- `renormalizer/tn/symbolic_ttno.py`

调用链：

```text
TTNO(basis_tree, terms)
  -> construct_symbolic_ttno(basis_tree, terms)
  -> symbolic_mo_to_numeric_mo_general(...)
```

`construct_symbolic_ttno()` 先把 `List[Op]` 转成树上的 symbolic matrix operator。不同 product terms 的公共 identity strings、公共 subtree 结构、公共 bridge/lead/phonon pattern 会通过 operator bond 被共享。

`symbolic_mo_to_numeric_mo_general()` 再把每个 tree node 的 symbolic operator entries 转成数值 tensor：

1. 对 node 上的 `basis_sets` 建一个局部 `Model`。
2. 对 symbolic entry 里的每个 `Op` 调 `split_elementary()`。
3. 对每个 local basis 调 `basis.op_mat(symbol)`。
4. 用 `tensordot` 形成该 node 的 physical up/down operator tensor。

最终 TTNO node tensor 的物理轴是 up/down 交错结构，虚拟轴是 operator bond。

## 7. Op 到当前 SOPBaselineOperator

核心文件：`renormalizer/tn/sop_baseline.py`

调用链：

```text
SOPBaselineOperator.from_symbolic_terms(terms, basis_tree)
  -> SOPTerm.from_op(op, basis_tree)
  -> _split_op_by_tree_node(op, basis_tree)
```

`_split_op_by_tree_node()` 用的是 `basis_tree.dof2idx`，不是线性 MPS site index。它把一个 product term 分成：

```python
SOPTerm(
    coeff=<scalar>,
    local_ops={node_idx: local_Op_on_that_tree_node}
)
```

缺失的 node 表示 identity。

当前 no-env apply 逻辑：

```text
apply_to_ttns(psi)
  -> apply_to_ttns_no_env(psi)
  for each SOPTerm:
      _apply_term_to_ttns(term, psi)
      result = result.add(term_psi)
```

`_apply_term_to_ttns()` 遍历每个 TTNS node：

- 如果该 term 在该 node 上没有 local op，跳过 physical matrix multiplication。
- 如果有 local op，调用 `_local_matrix_factors()` 得到每个 local basis 的矩阵。
- 用 `_apply_matrix_on_axis()` 把矩阵乘到对应 physical axis。
- root tensor 上乘 term coefficient。
- 更新 qn metadata。

这条路径没有 contraction environment。它只是避免了 per-term TTNO construction，并缓存了 local matrix factor。

整理后的 API 约定：

- `apply_to_ttns(psi)` 默认等价于 `method="sop_no_env"`。
- `apply_to_ttns(psi, method="sop_no_env")` 和 `apply_to_ttns_no_env(psi)` 是当前 naive baseline。
- `method="no_env"` 是短别名。
- `method="sop_with_env"` / `"with_env"` 在真正实现前必须明确抛出 `NotImplementedError`，避免 benchmark 误把 no-env 路径标成 with-env。

## 8. Op 到 contraction environment

现有 TTNO-with-env 路径：

```text
TTNO terms
  -> TTNO tensor network
  -> TTNEnviron(ttns, ttno)
  -> hop_expr1 / hop_expr2
  -> local effective Hamiltonian action
```

`TTNEnviron` 的 environment tensor 已经包含：

- bra branch
- TTNO branch
- ket branch

full-state `SOPBaselineOperator.apply_to_ttns(..., method="sop_with_env")` 仍未实现，必须继续抛出 `NotImplementedError`，避免误标 benchmark。

当前 adaptive benchmark 已实现 one-site local effective action 版本：

```text
benchmarks/benchmark_adaptive_operator_env.py::SOPOneSiteEffective
```

它的逻辑是：

```text
SOP terms
  -> group local_ops by tree branch/operator signature
  -> build branch environments once per signature
  -> for active node combine branch environments term-by-term
```

这样可以保留 flat SOP 表示，同时减少不同 product terms 之间重复 contraction state tree 的开销。

注意这里的 environment 是 contraction cache，不是 lead/phonon bath。它减少 state tree 上 branch contraction 的重复；TTNO 进一步通过 operator bond 压缩 SOP terms 之间重复的 operator structure。

## 9. 本 benchmark 中 `n_sop_terms` 的具体含义

`benchmarks/benchmark_adaptive_operator_env.py::build_hubbard_junction_case()` 构造 Hubbard junction term list。

每个 `n_lead` 生成四组 fermionic lead modes：

```text
L_i, L^i, R_i, R^i
```

所以 lead mode 总数是 `4 * n_lead`。每个 lead mode 对 Hamiltonian 贡献 3 个 product `Op`：

```text
1. c^\dagger c
2. c^\dagger Z... d
3. c Z... d^\dagger
```

因此 lead 部分 SOP term count 是：

```text
12 * n_lead
```

每个 phonon mode 贡献：

```text
p^2, x^2, n_{s^} x, n_{s_} x
```

即 `4 * n_phonon` 个 product terms。默认 `ed=0` 和 `ud=0`，bridge onsite / Hubbard U 项被 simplify 后不计数。因此当前 benchmark：

```text
n_sop_terms = 12 * n_lead + 4 * n_phonon
```

例子：

```text
n_lead=128, n_phonon=0:
  n_sop_terms = 1536

n_lead=64, n_phonon=16:
  n_sop_terms = 832
```
