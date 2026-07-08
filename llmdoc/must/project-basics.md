# 项目基础

Renormalizer 是面向电子-声子量子动力学的 Python 张量网络包。主 README 中已有功能包括 MPS/MPO、TTNS/TTNO、自动 Hamiltonian operator 构造、有限温动力学和量子数守恒。

当前工作树位于：

```text
/curie-home/yuxiong/Reno-quantity
```

当前分支背景是 `feat/mctdh-sop-comparison`，上一个 commit `5fbf5a1 Update SOP operator` 新增了 flat SOP baseline、SOP vs TTNO benchmark、相关测试和说明文档。

## 术语约定

- physical environment：模型里的 lead、phonon、bath 等物理自由度。
- contraction environment：张量网络缩并缓存，表示 active node / active subtree 外部网络缩并后的边界张量。
- SOP：sum of products，代码里主要表现为 `List[Op]` 或 `OpSum`。
- TTNO：tree tensor network operator，将 Hamiltonian term list 压缩成树形 operator tensor network。
- TTNS：tree tensor network state。

本轮讨论中的 environment 一律指 contraction environment，不指 lead / phonon bath。
