# 文档缺口

当前已初始化与 SOP/TTNO environment 任务直接相关的 llmdoc。

后续建议补充：

- SOP-with-env 实现完成后，更新 `llmdoc/architecture/ttns-ttno-environment.md`，把实际类名、函数名、cache key 设计写入稳定文档。
- benchmark 数据跑完后，新增结果解读文档，说明 `sop_no_env`, `sop_with_env`, `ttno_with_env` 三条曲线的实际 scaling。
- 如果后续修改 TDVP sweep 或 local effective Hamiltonian API，补充调用链图。
