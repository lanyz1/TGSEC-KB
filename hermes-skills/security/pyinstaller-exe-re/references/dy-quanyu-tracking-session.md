# 第三关实战：Dy全域追踪.exe（双层 PyInstaller + 服务器卡密）

CTF 考核第三关。98.6MB PyInstaller x64 onefile（Python 3.10），双层结构：launcher.pyc（Tk 卡密窗）+ payload/app_core.exe（84MB 原生 x64 功能体）。授权服务器 `http://59.153.167.211:4001`。

## 识别

```bash
# PE: x64 (0x8664), .text 仅 179KB 而文件 98.6MB → 数据/资源为主体 → 打包器
# 尾部 python310.dll + MEI magic @ 文件尾-88 → PyInstaller onefile, Python 3.10
python3 -c "d=open('x.exe','rb').read(); print(d[-80:])"   # python310.dll 明文在尾部
```

## 解包（注意版本）

```bash
uv python install 3.10          # PYZ 提取必须匹配 3.10 (3.12 会跳过 PYZ)
"C:\...\cpython-3.10.20\python.exe" pyinstxtractor.py dy.exe
# 999 文件, 入口: pyiboot01_bootstrap / pyi_rth_inspect / pyi_rth__tkinter / launcher.pyc
```

## launcher.pyc 反汇编（Tk 卡密验证壳）

pyc 头 16 字节（magic `6f0d0d0a` = 3.10），`marshal.loads(data[16:])` 取 code object，dis 输出到文件再 grep：

```bash
"$PY310" - <<'EOF' > launcher_dis.txt
import marshal, dis
data = open('launcher.pyc','rb').read()
dis.dis(marshal.loads(data[16:]))
EOF
grep -A 40 "call" launcher_dis.txt    # 看 call() 与 activate() 分支
```

**还原出的完整逻辑**：
- 常量：`SERVER="http://59.153.167.211:4001"`、`BRAND="Dy采集-监控"`、`_MEIPASS/payload/app_core.exe`
- `machine_id()` = `sha256(f"{COMPUTERNAME}|{PROCESSOR_IDENTIFIER}")`（无硬件 ID，跨机器稳定）
- `ensure_runtime_files()`：payload 下文件拷到 `%LOCALAPPDATA%/Dy采集-监控/`（CORE/ICON/assets/cache/db）
- `call(path, payload, timeout=6)`：POST `SERVER+path`，HTTPError 也尝试读 JSON body（返回 `{ok, msg, code, forceExit}` 或 None）
- `App.activate()`：`call('/api/activate', {card, machine_id})` → `result.get('ok')` 为真 → `save_config(token=..., remember_card, card)` → Popen CORE → 心跳线程
- `App.heartbeat()`：每 30s `call('/api/heartbeat', {token, machine_id})`，非 ok → 杀 CORE + 窗口 deiconify + "授权已失效"

## 服务端协议（curl 直测）

```bash
curl -X POST http://59.153.167.211:4001/api/activate -H 'Content-Type: application/json' \
  -d '{"card":"test","machine_id":"x"}'
# {"success":false,"ok":false,"code":"NOT_FOUND","msg":"卡密不存在","forceExit":true}
curl -X POST http://59.153.167.211:4001/api/heartbeat -H 'Content-Type: application/json' \
  -d '{"token":"faketoken","machine_id":"x"}'
# {"success":false,"ok":false,"code":"TOKEN_INVALID","msg":"授权已失效","forceExit":true}
```
code 语义：`NOT_FOUND`=卡密不存在、`TOKEN_INVALID`=token 失效、`NO_KEY`=缺卡密。卡密在服务器库 → 爆破无意义 → patch 本地 call()。

## 破解：重写 launcher.py + CArchiveWriter 重建

1. 按反汇编还原 `launcher_patched.py`，`call()` 改为：
```python
def call(path, payload, timeout=6):
    if path == "/api/activate":  return {"ok": True, "token": "CTF-BYPASS", "message": "激活成功"}
    if path == "/api/heartbeat": return {"ok": True}
    return {"ok": False}
```
2. 用 `CArchiveWriter(OUT, entries, 'python310.dll')` 重建（entry 4 元组，launcher 条目的 src 指向 .py 源码 + typecode 's'，writer 自动编译）。**重建细节与坑（Cookie 大端格式、writer "wb" 覆盖、'm'/'s' 裸 marshal 补头、git-bash 启动、_MEI 验证）见 SKILL.md"重建 exe"节 + Pitfalls 清单**——本关在重建上卡了 5+ 轮，全是这几点。
3. 验证：pyinstxtractor 重解包确认 launcher 已替换；运行输入任意卡密 → 直接 Popen app_core。

## 重建踩坑记录（2026-08 实测，5 轮失败教训）

| 轮次 | 做法 | 失败点 |
|---|---|---|
| 1 | 手写 cookie 解析（小端 `<i`） | **cookie 是大端 `!8sIIII64s`**，小端读出垃圾值且不报错 → 误判结构损坏 |
| 2 | 预写 bootloader 后调 CArchiveWriter | writer 用 `"wb"` 覆盖整个文件 → 输出变纯 package，无 MZ 头，exe 起不来 |
| 3 | CArchiveWriter + 'm' 条目给裸 marshal | `assert data[:4] == BYTECODE_MAGIC` 断言失败（'m' 需要 pyc 头） |
| 4 | CArchiveWriter + 's' 条目给裸 marshal | `source code string cannot contain null bytes`（'s' 会按源码编译；pyi_rth_* 是裸 marshal 的 's'） |
| 5 | 手写重建：保留原 TOC 字节流只改每条前 12 字节 offset/length/ulen | 待验证（结构已对，TOC 条目=entry_len(4)+!IIIIBc+name\0+16对齐） |
| 6 | **弃用手动重建 → pyinstaller 从 launcher_patched.py 全量重编译** | ✅ **一次成功**。`--onefile --add-data payload;payload --noconsole`，payload 先精简（删 .bak* 备份，322MB→81MB），exe 33MB 能跑 |

**最终方案（第 6 轮，成功）**：
1. `pyenv/Scripts/python.exe`（3.10 venv 装 pyinstaller 6.21）跑 `PyInstaller.__main__.run([...])`，入口 = 修改后的 launcher.py，`--add-data` 打包精简后的 payload 目录（Windows 分隔符 `;`）
2. 运行验证：`subprocess.Popen([exe])` 启动 → `%LOCALAPPDATA%/Dy采集-监控/` 生成 license.json + app_core.exe → 主窗口 \"Dy采集-全网追踪-目前已知最强的竞对追踪系统 v3.2.3\" 出现（乱码显示但 Responding=True）
3. **免登录直启版**（考核方要求双击直接进软件）：launcher 删掉 tk.Tk() 窗口，`main()` = save_config 预写 license + ensure_runtime_files + Popen(app_core) + 守护重启循环；`--noconsole` 打包。验证同 2

关键数据：`pkg_start=324096`（bootloader 长度）；launcher 条目 `pos=16042 c_len=4592 u_len=7986 type='s'`；绝对位置 = pkg_start + pos = 340138，数据头 `78da`（zlib 压缩）。

## 其他情报

- payload/douyin_system.db 是作者的 SQLite 使用数据（system_settings/web_cookies/fg_accounts/leads 等抖音营销表），与破解无关但泄露功能全貌
- 3 个 `.bak_*` 备份 exe（fanspro/fg_addaccount_gate/visible）= 作者迭代痕迹，可忽略
- app_core.exe = 原生 x64（.rdata 67MB，含 Electron/Qt5/CEF/chromium 引用——是它内部用的浏览器引擎，不是 Electron 打包），无 MEI magic
