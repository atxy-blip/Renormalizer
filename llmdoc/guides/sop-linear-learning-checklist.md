# SOP 线性学习清单：12 × 45 分钟

这是一条从“能运行”到“能给老师讲明白”的单线路线。唯一主教材是
[`notebooks/sop_debugging_lab.ipynb`](../../notebooks/sop_debugging_lab.ipynb)。

当前 Session：`____ / 12`<br>
上次停止位置：`________________`<br>
今天只做一个 Session：`是 / 否`

## 使用规则

每次只做一个 45 分钟 Session：

| 时间 | 动作 |
| --- | --- |
| 0–5 分钟 | 不看答案，复述上一节 |
| 5–30 分钟 | 运行 cell、检查真实对象或使用指定断点 |
| 30–40 分钟 | 写下公式、代码对象和观察结果 |
| 40–45 分钟 | 用三句话口述 |

只有同时留下“文字答案 + 一个实际数值或 shape + 三句话口述”才能勾选。
运行过 cell 但没有留下证据，不算完成。

卡住超过 10 分钟时：

1. 不继续搜索其他文件；
2. 找到本节的 expected observation；
3. 写下“我的实际值”和“预期值”；
4. 标出两者第一处不同；
5. 到 45 分钟立即停止，把差异写入“剩余问题”。

## 第一次启动

第一次注册现有 `reno-3.9` kernel：

```bash
conda run -n reno-3.9 python -m ipykernel install \
  --user --name reno-3.9 --display-name "Python (reno-3.9)"
```

从仓库根目录启动：

```bash
conda run -n base jupyter lab notebooks/sop_debugging_lab.ipynb
```

第一遍始终保持：

```python
RUN_BREAKPOINTS = False
```

## 总进度

| 完成 | Session | 必须留下的证据 | 日期 | 剩余问题 |
| --- | ---: | --- | --- | --- |
| [ ] | 1 | 启动记录和完整实验数据流 | ____ | __________________ |
| [ ] | 2 | 一个 `Op`/`SOPTerm` 实例对照 | ____ | __________________ |
| [ ] | 3 | dof 到 node 的真实映射 | ____ | __________________ |
| [ ] | 4 | symbolic operator 到矩阵/axis 对照 | ____ | __________________ |
| [ ] | 5 | 13-term no-env 完整累加证据 | ____ | __________________ |
| [ ] | 6 | strict directed-edge cache 证据 | ____ | __________________ |
| [ ] | 7 | `91 → 33` 的解释和边界 | ____ | __________________ |
| [ ] | 8 | TTNO bond/environment 复用证据 | ____ | __________________ |
| [ ] | 9 | 三条正式路径的 status、误差和 quantity | ____ | __________________ |
| [ ] | 10 | `189 → 63 → 18 → PDF/PNG` 数据链 | ____ | __________________ |
| [ ] | 11 | 主文与 SI 每个 panel 的一句话 | ____ | __________________ |
| [ ] | 12 | 一次不看资料的 5–8 分钟汇报 | ____ | __________________ |

---

## Session 1：环境与完整实验地图

- [ ] Session 1 完成

对应：setup cell + Investigation 1。

### 0–5 分钟：建立起点

在纸上写：

```text
我现在不知道的三个问题：
1.
2.
3.
```

### 5–30 分钟：运行

1. 启动 notebook。
2. 确认 kernel 是 `Python (reno-3.9)`。
3. 从 setup cell 运行到 Investigation 1。
4. 找到并抄下：
   - `n_modes`
   - `state_bond`
   - `primitive_basis`
   - `quantity`
   - `sop.n_terms`
5. 把输出的数据流补全：

```text
symbolic Op terms
→ Li2024 BasisTree + TTNS
→ SOPBaselineOperator or TTNO
→ all-node local effective actions
→ atomic NPZ snapshot
→ raw/summary/fits CSV
→ three-panel figure
```

### 30–40 分钟：必须回答

哪些步骤改变 Hamiltonian/state 的表示，哪些步骤只负责记录、汇总、拟合或绘图？

```text
改变表示：

不改变测量值，只处理结果：
```

### 40–45 分钟：三句话

1. 我们先构造同一个 Hamiltonian 和 TTNS。
2. 三条方法改变的是 operator/environment 的表示与复用方式。
3. snapshot、summary、fit 和 plot 不重新定义被测 quantity。

完成证据：写出 `quantity = local_effective_1site_apply_all_nodes`，并能完整复述上面的七步数据流。

停止规则：如果 notebook 无法启动，只记录完整报错和 kernel 名，不进入 Session 2。

---

## Session 2：一个 `Op` 如何变成 `SOPTerm`

- [ ] Session 2 完成

对应：Investigation 2。

### 0–5 分钟：复述

不看 Session 1，写出从 symbolic term 到 figure 的七步链。

### 5–30 分钟：运行与检查

1. 运行 Investigation 2。
2. 比较 `symbolic_rows[0]` 与 `symbolic_rows[-1]`。
3. 检查：
   - `op.symbol`
   - `op.dofs`
   - `op.factor`
   - `SOPTerm.coeff`
   - `SOPTerm.local_ops`
4. 第二遍需要断点时，停在
   `SOPTerm.from_op()` 的：

```python
local_ops, coeff = _split_op_by_tree_node(op, basis)
```

公式：

$$
H=\sum_l c_l\prod_\kappa h_l^{(\kappa)}.
$$

### 30–40 分钟：必须回答

```text
一个 Op 保存：

一个 SOPTerm 把 scalar 保存为：

按 tree node 保存的内容是：

为什么没有为每个 node 显式保存 identity：
```

### 40–45 分钟：三句话

1. `Op` 是带 coefficient 和 dof 标签的 symbolic product term。
2. `SOPTerm.from_op` 把 scalar coefficient 与 node-local factors 分开。
3. 没有出现在 `local_ops` 中的 node 表示 identity，因此不必显式存储。

完成证据：记录真实的 `sop.n_terms = 13`，并抄下一个 coupling term 的
`factor`、`coeff` 和非平凡 local-op 数。

停止规则：不能解释 coefficient 在哪里乘入时，停在本节，不进入 tree mapping。

---

## Session 3：product term 如何定位到 tree node

- [ ] Session 3 完成

对应：Investigation 3。

### 0–5 分钟：复述

不看答案解释 `Op → SOPTerm`，必须说出 `coeff` 和 `local_ops`。

### 5–30 分钟：运行与检查

1. 运行 Investigation 3。
2. 查看 `tree.dof2idx`。
3. 对选中的 `sigma_z x` coupling term，记录每个 node 的：
   - `node_index`
   - `dofs`
   - `physical_bond_dims`
   - `is_nontrivial`
4. 第二遍断点停在 `_split_op_by_tree_node()` 中：

```python
node_indices = {basis.dof2idx[dof] for dof in elementary_op.dofs}
```

### 30–40 分钟：必须回答

```text
spin dof → node:
v_3 dof → node:
非平凡 node:
其他 node 被省略的原因:
```

当前固定小例中，`v_3` 位于 node 6，`spin` 位于 node 7。

### 40–45 分钟：三句话

1. `Op.split_elementary()` 先按 dof 分开 elementary operators。
2. `BasisTree.dof2idx` 决定每个 factor 属于哪个 tree node。
3. 同一 node 的 factors 会相乘，其他 node 是隐式 identity。

完成证据：写出 node 6 和 node 7 的 operator symbol，并解释其余六个 node 为什么是 identity。

停止规则：不要试图背整棵 tree；只追踪选中的一个 coupling term。

---

## Session 4：symbolic local operator 如何变成数值矩阵

- [ ] Session 4 完成

对应：Investigation 4。

### 0–5 分钟：复述

画出：

```text
dof → dof2idx → node → local basis → numeric matrix
```

### 5–30 分钟：运行与检查

1. 运行 Investigation 4。
2. 记录：
   - concrete basis class
   - `basis_set.nbas`
   - `elementary_op.symbol`
   - `operator_matrix.shape`
   - `identity_matrix.shape`
   - `operator_matrix.dtype`
3. 查看实际解析到的 `BasisSHO.op_mat`。
4. 第二遍断点停在 `BasisSHO.op_mat()` 返回前。

公式：

$$
[h_l^{(\kappa)}]_{ij}
=\langle i|h_l^{(\kappa)}|j\rangle .
$$

### 30–40 分钟：必须回答

```text
local basis dimension:
matrix input/output dimension:
对应 TTNS tensor 的 physical axis:
local scalar factor 在哪里应用:
```

### 40–45 分钟：三句话

1. 具体 `BasisSet` 负责把 symbolic operator 转成局域数值矩阵。
2. 矩阵维数必须等于该 node 的 physical basis dimension。
3. SOP helper 缓存 local matrices，但这不是 contraction environment cache。

完成证据：记录本例 `BasisSHO` 的 `3 × 3` operator matrix，并指出它作用于哪个 physical axis。

停止规则：如果 tensor axis 看不清，只画 matrix 的 input/output index，不追求一次理解 einsum。

---

## Session 5：完整 no-environment SOP application

- [ ] Session 5 完成

对应：Investigation 5。

### 0–5 分钟：复述

写出：

$$
H|\Psi\rangle
=\sum_l c_l\left(\prod_\kappa h_l^{(\kappa)}\right)|\Psi\rangle .
$$

### 5–30 分钟：运行与检查

1. 运行 Investigation 5。
2. 检查一个 term 在每个 node 作用前后的 tensor shape。
3. 检查完整调用：

```python
sop.apply_to_ttns_no_env(psi)
```

4. 记录：
   - `n_terms_accumulated`
   - `single_term_tensor_elements`
   - `final_state_tensor_elements`
   - `input_max_bond`
   - `final_max_bond`
5. 第二遍断点依次停在：
   - `for term in self.terms`
   - `result = result.add(term_psi)`
   - `_apply_term_to_ttns` 的 node loop

### 30–40 分钟：必须回答

```text
每个 term 独立重复的 tree 工作：

13 个 term 如何进入最终 result：

为什么这是 full-state H|psi>：

为什么它不是正式 benchmark 的 all-node local-action quantity：
```

当前小例应看到 13 个 term、input max bond 2、final max bond 26。

### 40–45 分钟：三句话

1. no-env 路径对每个 SOP term 独立复制并作用整棵 TTNS。
2. 每个 term state 通过 `result.add(term_psi)` 进入最终和。
3. 这演示 full-state `H|psi>`，而正式计时比较的是 all-node local effective actions。

完成证据：写出 13、2、26 三个数，并准确说出 full-state 与 formal quantity 的区别。

停止规则：不要在本节尝试推导正式 scaling；先确认完整 term loop 和最终求和。

---

## Session 6：strict directed-edge state environment

- [ ] Session 6 完成

对应：Investigation 6。

### 0–5 分钟：复述

不用代码解释 no-env 路径重复了什么。

### 5–30 分钟：运行与检查

1. 运行 Investigation 6。
2. 查看 `SOPMCTDHSweepEnvironment._env_cache`。
3. 记录 cache key：

```text
(source_node_idx, target_node_idx, term_index)
```

4. 检查一个 key、reverse key 和 message tensor shape。
5. 第二遍断点在 strict environment 构造 directed-edge message 后停止。

本例中：

```text
n_nodes = 8
n_terms = 13
n_entries = 2 × (8 - 1) × 13 = 182
```

### 30–40 分钟：必须回答

```text
source → target 表示：

为什么 reverse key 是另一条 message：

为什么 key 必须包含 term_index：

strict path 复用了什么：

strict path 没有复用什么：
```

### 40–45 分钟：三句话

1. 每条 directed edge 保存“从 source subtree 看向 target”的 state message。
2. strict baseline 在同一个 SOP term 内复用 state contractions。
3. 因为 key 包含 `term_index`，它不跨 terms 合并相同 operator structure。

完成证据：推导并记录 `182`，同时解释为什么不能只写成无向 edge cache。

停止规则：如果方向含义混乱，只追踪一个 key 和它的 reverse key。

---

## Session 7：term cache 与 signature cache

- [ ] Session 7 完成

对应：Investigation 7。

### 0–5 分钟：复述

写出 strict cache 的完整三元 key。

### 5–30 分钟：运行与检查

1. 运行 Investigation 7。
2. 比较：
   - `term_entries`
   - `signature_entries`
   - representative term keys
   - representative signature keys
   - `signature_metadata`
3. 确认：

```text
term entries      = 91
signature entries = 33
```

4. 找出两个不同 terms 共享 branch/operator signature 的实例。

### 30–40 分钟：必须回答

```text
91 的 key 身份依据：

33 的 key 身份依据：

为什么 33 < 91：

为什么 signature cache 不是 strict MCTDH-like baseline：
```

### 40–45 分钟：三句话

1. term cache 把不同 SOP terms 始终当作不同对象。
2. signature cache 允许相同 branch operator structure 跨 terms 共享。
3. 因此它是 optimized、explanatory、non-strict，不能替代正式 strict baseline。

完成证据：写出 `91 → 33`，并能说出“减少的不是物理 Hamiltonian terms，而是重复 cache identities”。

停止规则：如果只记住“33 更快”但说不出跨 term sharing，本节不能勾选。

---

## Session 8：TTNO operator bond 与 environment

- [ ] Session 8 完成

对应：Investigation 8。

### 0–5 分钟：复述

分别用一句话定义 strict term cache 和 signature cache。

### 5–30 分钟：运行与检查

1. 运行 Investigation 8。
2. 记录：
   - TTNO node 数；
   - `ttno.bond_dims`；
   - `max_bond`；
   - 每个 TTNO tensor shape；
   - representative environment-parent shape。
3. 区分：
   - `TTNO.apply()`；
   - `TTNEnviron`；
   - `hop_expr1()`。

当前小例应看到 8 个 nodes、最大 operator bond 3、representative environment shape `(2, 3, 2)`。

### 30–40 分钟：必须回答

```text
TTNO bond index 表示：

TTNO 跨 terms 共享的对象：

TTNEnviron 复用的对象：

为什么 TTNO.apply() 不等于 local-effective-Hamiltonian environment path：
```

### 40–45 分钟：三句话

1. TTNO bond 把多个 product terms 的公共 operator subtree 压缩到同一网络中。
2. `TTNEnviron` 保存 state/operator 网络在 active node 外部的缩并边界。
3. 正式 TTNO path 同时利用 operator-bond sharing 和 contraction environment。

完成证据：记录 `max_bond = 3` 和 `(2, 3, 2)`，并正确区分 `TTNO.apply()` 与 `hop_expr1()`。

停止规则：不要用“TTNO 就是一个大矩阵”代替 operator-bond 解释。

---

## Session 9：正确性、方法身份和计时边界

- [ ] Session 9 完成

对应：Investigation 9。

### 0–5 分钟：复述

不看资料写出三条正式方法的准确 label。

### 5–30 分钟：运行与检查

1. 运行 Investigation 9。
2. 完成下表：

| Method | status | relative error vs TTNO | 复用对象 |
| --- | --- | ---: | --- |
| `sop_no_env` | ____ | ____ | ____ |
| `sop_mctdh_like_state_env` | ____ | ____ | ____ |
| `ttno_with_env` | ____ | ____ | ____ |

3. 记录每条 row 的：
   - `quantity`
   - `time_env_build_sec`
   - `time_apply_sec`
   - `time_total_sec`
4. 确认三个 status 的集合只有 `ok`。

### 30–40 分钟：必须回答

```text
三条方法如何证明在算同一物理对象：

relative error 的参照：

正式 quantity：

这个 quantity 不是什么：
```

必须写出：

```text
local_effective_1site_apply_all_nodes
```

它不是完整 TDVP propagation，也不是 Session 5 的 full-state `H|psi>`。

### 40–45 分钟：三句话

1. 三条方法对同一个 all-node local-action quantity 给出数值一致结果。
2. 它们的差异来自 state/operator structure 的复用，而不是物理问题不同。
3. 计时结果只能陈述为 local effective-action benchmark，不能扩大成完整 TDVP step。

完成证据：三行 status 都是 `ok`，并记录最大 relative error 的数量级。

停止规则：如果无法一句话定义 quantity，不读取 scaling exponent。

---

## Session 10：manifest、snapshot、summary、fit 和 plot

- [ ] Session 10 完成

对应：Investigation 10。

### 0–5 分钟：复述

写出正式 quantity 和三个 method labels。

### 5–30 分钟：运行与检查

1. 运行 Investigation 10。
2. 找到选中的真实 manifest task 和 snapshot path。
3. 确认：
   - manifest records：189；
   - repeat IDs：0、1、2；
   - completed snapshots：189；
   - missing task IDs：空；
   - summary rows：63；
   - fit rows：18；
   - plot 输出：PDF + PNG，均非空。
4. 写出真实函数链：

```text
read_task
→ load_snapshot / collect_snapshots
→ summarize
→ compute_fits
→ plot
```

### 30–40 分钟：必须回答

```text
为什么一个 task 必须 immutable：

为什么 snapshot 必须 atomic：

为什么 189 / 189 之前不能称为 final：

summary 为什么从 189 变为 63：

18 fits 分别来自哪些 panel/method/window 组合：
```

核心数据链：

```text
189 manifest tasks
→ 189 status=ok snapshots
→ 63 repeat-aggregated summary rows
→ 18 scaling fits
→ PDF + PNG
```

### 40–45 分钟：三句话

1. manifest 固定每个参数点、方法和 repeat 的身份。
2. 每个 task 原子写 snapshot，finalizer 只接受完整的 `status=ok` 集合。
3. 汇总、拟合和绘图处理同一批记录，不改变 scientific quantity。

完成证据：不看 notebook 写出 `189 → 189 → 63 → 18 → PDF/PNG`。

停止规则：如果数字记混，只重新追踪一个 task，不重跑任何正式 Slurm array。

---

## Session 11：主文图与 Supporting Information

- [ ] Session 11 完成

对应：三张正式 Nature-style 图。

### 正式图件位置

投稿使用 PDF；PNG 只用于快速预览和版式检查。

| 用途 | PDF | PNG 预览 |
| --- | --- | --- |
| 主文核心图 | [Li.W.2024 三方法标度图](../../benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.pdf) | [预览](../../benchmarks/results/operator_env_scaling/final/li2024_spin_boson_20260713_scaling_three_panel.png) |
| SI Figure S1 | [Complexity validation](../../benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.pdf) | [预览](../../benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/complexity_validation.png) |
| SI Figure S2 | [Model mechanism](../../benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.pdf) | [预览](../../benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/model_mechanism.png) |

旧 `ren_formal_partial` 只有 204/216 个任务；historical strict-all-node 图缺少
tracked raw CSV。两者都不能列为当前最终投稿图。

### 0–5 分钟：复述

不看表格说出主文图和两张 SI 图各自回答什么问题。

### 5–30 分钟：逐 panel 阅读

#### 主文图

对每个 panel 写一句话：

```text
(a) N_b：
(b) M_s：
(c) d：
```

必须读出 largest-four-point wall-time exponents：

| Panel | no env | strict state env | TTNO + env |
| --- | ---: | ---: | ---: |
| `N_b` | 3.109 | 2.035 | 0.916 |
| `M_s` | 2.180 | 2.243 | 2.223 |
| large `d` | -0.004 | 0.002 | 0.024 |

#### SI Figure S1：complexity validation

写下它支持的三项机制：

```text
full-rank internal node：
paired two-mode leaf：
primitive-contracted one-mode leaf：
```

正确边界是：

- internal optimized FLOPs 为 `M_s^4`；
- paired leaf 的数学/storage behavior 为 `d^4`；
- primitive-contracted leaf 为 `d^2`；
- isolated wall-time tail 可以低于精确 FLOP power。

#### SI Figure S2：model mechanism

给四类证据各写一句话：

```text
full-model total time：
construction/environment/local-action stages：
state/operator storage：
peak process memory：
```

### 30–40 分钟：必须回答

```text
为什么主文图能支持三条 operator path 的核心比较：

为什么 S1 属于数学/isolated-kernel 支撑：

为什么 S2 属于 mechanism/memory 支撑：

为什么 full-workflow M_s≈2.2 不否定 internal FLOPs M_s^4：

为什么 large-d wall time≈constant 不等于 leaf complexity O(1)：
```

### 40–45 分钟：三句话

1. 主文图展示同一 all-node quantity 下三种复用策略的正式 wall-time scaling。
2. SI S1 用 FLOPs 和 isolated kernels 证明 `M_s^4`、`d^4` 与 `d^2` 的 tensor 机制。
3. SI S2 用阶段时间、storage 和 memory 解释这些机制如何进入完整模型。

完成证据：为三张图的每个 panel 写一句话，并能解释 wall-time exponent 与 FLOP complexity 不等价。

停止规则：不要试图在一节内写完整论文 caption；本节只完成“每个 panel 一句话”。

---

## Session 12：给老师的 5–8 分钟完整汇报

- [ ] Session 12 完成

对应：notebook 的 Oral Recap。

### 0–5 分钟：空白纸准备

只写六个标题，不写内容：

```text
1. Problem
2. Modification
3. Reason
4. Mechanism
5. Measured effect
6. Scientific boundary
```

### 5–30 分钟：第一次口述

不看 notebook，用 5–8 分钟按以下顺序讲：

1. 问题：原 flat SOP no-env comparison 为什么可能不公平？
2. 修改：增加了 strict per-term directed-edge state environment。
3. 原因：把 state contraction reuse 与 TTNO operator-structure reuse 分开。
4. 机制：no-env、strict state env、TTNO + env 分别复用什么。
5. 效果：`N_b` tail exponents 为 3.109、2.035、0.916。
6. 验证：189/189 snapshots，三条方法数值一致。
7. 边界：不是 full TDVP step；`M_s^4`/`d^4`/`d^2` 来自分层 diagnostics。
8. 图件：一张主文图，两张 SI 支撑图。

录音或请同伴计时。中途卡住时只在纸上标记，不立刻看答案。

### 30–40 分钟：老师追问自检

逐题给出不超过三句话的回答：

1. 为什么 `sop_mctdh_like_state_env` 可以称为 strict？
2. 为什么 `sop_env_plus_operator_cache` 不能进入正式三方法比较？
3. `TTNO.apply()` 与 `TTNEnviron + hop_expr1()` 有什么不同？
4. 为什么正式 quantity 不是完整 propagation？
5. `N_b^3/N_b^2/N_b` 分别对应什么重复工作或复用？
6. 为什么 `M_s` wall-time 约 2.2，但 internal contraction 是 `M_s^4`？
7. 为什么 adaptive contraction 后 large-`d` wall time 近常数？
8. 为什么旧 Hubbard partial 图不能作为最终论文图？

### 40–45 分钟：评分与第二次口述决定

每项 0、1、2 分：

| 项目 | 0 | 1 | 2 | 得分 |
| --- | --- | --- | --- | ---: |
| 修改讲清楚 | 没说 | 说名称 | 说代码对象与行为 | __ |
| 原因讲清楚 | 没说 | 说“更快” | 说公平比较与复用边界 | __ |
| 机制讲清楚 | 混淆 | 能区分两条 | 能区分三条及 signature cache | __ |
| 效果有证据 | 没数字 | 有部分数字 | 有 189/63/18 和核心指数 | __ |
| 科学边界 | 扩大结论 | 提到部分边界 | 正确区分三种 timing/complexity | __ |

```text
总分：____ / 10
下一次只修正的最低分项：
```

完成标准：

- 总分至少 8/10；
- 没有任何一项为 0；
- 全程没有阅读 notebook 的 Oral Recap；
- 能准确指出主文图和两张 SI 图的 PDF。

三句话最终版本：

1. 我增加 strict per-term state environment，是为了从 flat SOP 的重复 tree contraction 中分离 state reuse，而不偷偷引入跨 term operator sharing。
2. 在相同 all-node local-action quantity 上，no-env、strict state env 和 TTNO + env 的 `N_b` tail exponents 分别是 3.109、2.035 和 0.916，并且 189/189 个任务数值一致。
3. 这些是 operator-kernel wall-time 结果；internal `M_s^4`、paired-leaf `d^4` 和 contracted-leaf `d^2` 由 Supporting Information 的分层 diagnostics 单独支撑。

停止规则：不足 8 分时不要重学全部 12 节，只回到最低分对应的一个 Session。

---

## 完成后的最短汇报提纲

```text
原问题：
flat SOP no-env 重复整棵 tree contraction，可能夸大 SOP 与 TTNO 的差距。

修改：
加入 strict per-term directed-edge state environment，同时保留 no-env 和 TTNO + env 对照。

为什么：
把 state contraction reuse 与跨 term operator-structure reuse 分开比较。

效果：
N_b tail：3.109 → 2.035 → 0.916；189/189 tasks status=ok，数值误差在容差内。

机制：
no-env 不复用 tree environment；strict path 只复用每个 term 的 state messages；
TTNO path 还通过 operator bonds 共享 operator structure。

边界：
正式 quantity 是 local_effective_1site_apply_all_nodes，不是 full TDVP step。
full-workflow wall time 与 isolated FLOP complexity 必须分开。

图件：
主文放 Li.W.2024 three-panel scaling；
SI 放 complexity validation 和 model mechanism。
```
