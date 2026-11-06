## 常见坑与陷阱（跨平台共性）

- **只看磁盘版本就下结论**：Linux 的 init-only 段在运行时已消失、macOS 的 AuxKC 可能还在跑旧版本、Android 可能加载的是另一分区的同名模块——**先对齐"磁盘 / 运行 / 加载集合"三份身份**
- **把"看着像坏"的合法形态当损坏**：Linux 的签名尾、livepatch 节、split BTF 都不是损坏（见 [[linux-kernel]] 的四类形态）
- **用同版本假设解释 offset 或符号错误**：RANDSTRUCT、MODVERSIONS、KMI 分支都会让"同版本"实际不同
- **单一视图判定"没有 hook / 没有隐藏模块"**：`lsmod`、syscall table、`/sys/module` 任一为干净都不构成结论——必须 cross-view，且**视图矛盾时优先信离线内存取证**
- **hook 手法只盯着老几样**：现代落点包括 operation 结构、ftrace、kprobes、inline text——"syscall table 没被 hook"不等于内核干净
- **内核态操作没有隔离**：加载/触发内核代码可能直接宕机（Windows 蓝屏）；一切在调试 VM + 快照内做（[[re-sandbox]] 最高原则）
- 各平台特有的坑见对应分支（[[windows-kernel]] / [[linux-kernel]] / [[macos-kernel]] / [[android-kernel]]）
