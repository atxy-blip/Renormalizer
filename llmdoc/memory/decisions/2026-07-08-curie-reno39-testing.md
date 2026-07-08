# 决策：Curie 上使用 reno-3.9 测试

日期：2026-07-08

## 决策

本仓库在 Curie 本机运行测试和 benchmark 时，统一使用 conda 环境：

```bash
conda run -n reno-3.9 python ...
```

## 背景

当前 shell 中裸 `python` 不在 PATH，而 `conda run -n reno-3.9 python` 可用，已验证 Python 版本为 3.9.20。

## 影响

- llmdoc 启动文档和测试指南均以 `reno-3.9` 为标准。
- 后续实现 SOP environment 和 benchmark 时，验证命令也使用该环境。
- 如果需要临时源码调查，可使用 `python3`，但不作为正式测试环境。
