## 操作步骤（跨平台通用主线）

1. **确认身份**：这是哪一份（磁盘 / 运行 / 加载集合中的版本）、什么构建（vermagic / CRC / KMI / 签名）、什么形态（PE / ET_REL / Mach-O / 用户态 dext）
2. **类型与符号**：优先官方类型来源（PDB / BTF / 符号表 / KMI list），其次精确构建信息，最后才是推断
3. **功能骨架**：从 imports/exports 与内核 API 调用关系切分功能——闭源或 stripped 时这一步尤其有效
4. **hook 与隐藏**：枚举 hook 落点（表项 / inline text / 回调数组 / operation 结构）+ **cross-view 交叉**（用户态视图 vs 内核真实对象与内存）
5. **验证与收尾**：运行时核对（调试器 / kprobe / IORegistry / 内存侧），结论与证据按 [[re-analyze/analysis-contract]] 入档

