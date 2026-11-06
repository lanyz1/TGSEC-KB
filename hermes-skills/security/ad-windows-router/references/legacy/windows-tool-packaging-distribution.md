<!-- archived from /root/.hermes/skills/security/windows-tool-packaging-distribution/SKILL.md on 2026-10-21 -->

---
name: windows-tool-packaging-distribution
description: >-
  测绘引擎·Package Python tools as Windows exe for customers.
owned: true
tier: general
pack: survey-skill
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-tool-packaging-distribution`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-tool-packaging-distribution/…')`，不要相对 `references/legacy/` 解析。

# windows-tool-packaging-distribution（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/windows-tool-packaging-distribution/`

溯源（仅标记）：`hermes/software-development`

---

# Windows 客户端工具打包与分发

把 Python 脚本/tkinter GUI 打包成 exe 分发给非技术客户：**客户零依赖**（无需 Python/Chrome），支持代理抓取（SOCKS5 认证桥）和**云端自动更新下发**。实战验证于 TikFlow 抓 CK 工具（GUI 版：IP 列表 + 右键抓取 + Cookie 列复制）。

## 交付结构（客户零依赖）

```
工具文件夹/
├── 工具.exe        ← PyInstaller --onefile --windowed 产物
├── chrome/         ← 内置便携 Chrome（Chrome for Testing，免安装）
└── 使用说明.txt    ← GBK 编码（客户记事本打开不乱码）
```

## 核心步骤

1. **GUI 用 tkinter**（Windows 自带，PyInstaller 零额外依赖；不要用 PyQt/electron）
   - 列表用 `ttk.Treeview` + 右键菜单 `tk_popup`，线程通信用 `queue + root.after(200, drain)`
   - 抓取/网络任务必须放 `threading.Thread(daemon=True)`，GUI 更新经 msg_q 泵回主线程
2. **打包**（独立 venv，避免污染主环境）：
   ```
   python -m venv $LOCALAPPDATA/Temp/pybuild
   pybuild/Scripts/pip install pyinstaller websocket-client
   pybuild/Scripts/pyinstaller --onefile --windowed --name 工具名 --distpath dist --workpath build --specpath . 主程序.py
   ```
3. **内置便携 Chrome**：Chrome for Testing（官方免安装）。下载走 **npmmirror 镜像**（Google storage 国内极慢，~160MB 会卡 2 小时）：
   ```
   https://registry.npmmirror.com/-/binary/chrome-for-testing/<version>/win64/chrome-win64.zip
   ```
   版本从 `googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json` 的 Stable 取。解压 `chrome-win64/` → 重命名为工具目录 `chrome/`，代码 `find_chrome()` 优先 `HERE/chrome/chrome.exe`，找不到退回系统 Chrome。
4. **云端更新下发**（见 references/cloud-update-push.md）：exe 启动后台 GET version.json → 版本不同弹窗 → 下载新 exe → update.bat 杀进程/覆盖/重启。

## 坑位清单（全部实战踩过）

1. **PyInstaller onefile 的 `__file__` 指向临时解压目录**（_MEIPASS），读不到 exe 旁的配置文件（proxy.txt/data.json）→ 必须：
   ```python
   HERE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
   ```
2. **exe 控制台是 GBK**：print 带 emoji（✅⏳🌐🎉）直接 `UnicodeEncodeError` 崩溃。exe 里禁用 emoji，全用中文/`[OK]` 标记。MessageBoxW 宽字符 API 不受影响。
3. **--windowed 静默崩溃**（错误不可见）→ 先打 console 版（去掉 --windowed）看 stderr 定位，修好再打 windowed。
4. **tkinter `simpledialog.askstring(width=60)` 抛 TypeError 被静默吞**（点击"无反应"！）——width 不是合法参数，去掉。`tk.Frame(pady=(0,10))` 元组同样非法（"bad screen distance"），Frame 构造用标量，`pack(pady=(0,10))` 才支持元组。
5. **bat 编码**：bat 文件必须 **GBK + CRLF**（python 写入：`content.replace('\r\n','\n').replace('\n','\r\n').encode('gbk')`）；**不要 `chcp 65001`**——它让 cmd 按 UTF-8 解析 GBK 内容 → 中文文件名参数乱码（python 找不到脚本）。
6. **Chrome 启动冲突**：先杀占用同调试端口的残留实例再启动；`--user-data-dir` 每任务独立（多实例并行不冲突）；CfT Chrome 必须带 `--user-data-dir`（默认会找系统 profile）。
7. **PyInstaller 中文 exe 名**：OK；但命令行传中文路径时注意 cmd/bash 编码差异（测试时用 `MSYS_NO_PATHCONV=1 cmd /c`）。

## SOCKS5 认证代理桥

Chrome `--proxy-server` **不支持 socks5 账号密码**。方案：本地起 HTTP CONNECT 桥 → 上游 SOCKS5（带认证），Chrome 连 `http://127.0.0.1:桥端口`。完整协议实现见 **references/socks5-bridge.md**（含关键坑：CONNECT 响应必须读完地址部分，否则 TLS 流污染 → ERR_SSL_PROTOCOL_ERROR）。代理地址支持 `#备注`（如 `#美国`）自动剥离。

## 客户更新流程（无自动更新机制的老版本）

- 老客户：发**手动更新包**（12MB）= 新 exe 改名 `工具_new.exe` + `更新.bat`（taskkill → copy 覆盖 → del → start → 自删）+ 说明.txt，客户解压到工具文件夹双击 bat。
- 更新包 zip 单独打（`Compress-Archive`），验证替换：比较 exe 字节数变化 + `_new.exe` 消失。
- 新客户：全量 zip（含 chrome/，~200MB）。之后全走云端自动更新。

## 验证清单

- [ ] exe 在无 Python 环境能启动（或至少 console 版无 traceback）
- [ ] 配置读写路径正确（frozen 模式 HERE = exe 目录）
- [ ] 中文/GBK 输出无崩溃
- [ ] 代理桥：CONNECT 200 + TLS 握手 + 出口 IP 正确（api.ipify.org 实测）
- [ ] update.bat 模拟目录跑通（exe 字节变化 + new 文件清理）
- [ ] version.json 可访问、版本比较逻辑对
