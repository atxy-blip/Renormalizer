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

当前 apply 逻辑：

```text
apply_to_ttns(psi)
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

SOP-with-env 还没有实现。合理方向是：

```text
SOP terms
  -> group local_ops by tree branch/operator signature
  -> build branch environments once per signature
  -> for active node combine branch environments term-by-term
```

这样可以保留 flat SOP 表示，同时减少不同 product terms 之间重复 contraction state tree 的开销。
