## 工具准备

本技能以纯静态分析为主（免沙箱，[[re-analyze/platform-tips]] 最高原则）；需要动态验证时转 [[re-fw-emulate]]。工具可替换，方法为核心。

### Ghidra（反编译与结构体定义主力）

- 下载: GitHub `NationalSecurityAgency/ghidra` releases，解压即用（无需安装）
- JDK 21（Ghidra 11.3+ 要求）:
  - Linux: `apt install openjdk-21-jdk` / `dnf install java-21-openjdk` / `pacman -S jdk21-openjdk`
  - macOS: `brew install openjdk@21` 或 `brew install --cask temurin`
  - Windows: `choco install temurin21`
- 启动: `./ghidraRun`（GUI）/ `./support/analyzeHeadless`（无头）
- 验证: `java -version`（须 21+）；`./support/analyzeHeadless -help` 正常输出
- 用法核心：Data Type Manager 定义 TCB/内核对象结构体后，类型传播会显著改善反编译质量

### binwalk（镜像提取先行）

- Linux: `apt install binwalk`（Debian/Ubuntu）/ `dnf install binwalk` / `pacman -S binwalk`
- pip（跨平台、版本新）: `pip install binwalk`
- macOS: `brew install binwalk`
- Windows/WSL: Windows 本机无官方包，用 WSL 内 Linux/pip 版
- 验证: `binwalk --version`

### python3（脚本化解析与批量标注）

- Linux: `apt install python3` / `dnf install python3` / `pacman -S python`
- macOS: 自带；Windows: 官方安装器或 `choco install python`
- 验证: `python3 --version`
- 用途: 批量搜特征串/魔数、按字段偏移解析任务表、生成 Ghidra 脚本自动标注任务名/入口

