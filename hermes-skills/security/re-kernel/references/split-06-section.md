## 工具准备（按平台，细节见各分支）

- **Windows**：[[re-ghidra]] / [[re-ida]]（导入 WDK 内核类型）、[[re-windbg]]（双机 / KDNET 内核调试）、Microsoft 公共符号；测试签名仅在调试 VM 内开启（`bcdedit /set testsigning on`，需关 Secure Boot）
- **Linux**：`readelf`/`objdump -r`（ET_REL 与 relocation）、`modinfo`（vermagic/依赖/签名/livepatch）、`pahole`/`bpftool`（BTF）、`bpftrace`/`perf probe`（kprobe）、`ftrace`
- **macOS**：`otool`/`vmmap`/`ioreg`/`kmutil`/`codesign -d --entitlements`/`lldb`（[[re-lldb]]、[[re-format-macho]]）
- **Android**：`modinfo`/`readelf` + 目标分支的 KMI symbol list 与 `Module.symvers` 比对

