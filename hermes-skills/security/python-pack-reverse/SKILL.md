---
name: python-pack-reverse
description: >-
  Nuitka / PyInstaller 授权包认族、列 TOC、抽 auth 模块名。
  触发：Nuitka、PyInstaller、PYZ、onefile、pyc 逆向。
  网络验证/卡密接着 net-license-crack。
---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='python-pack-reverse', file_path='references/full.md')`

# Python 打包逆向（测绘引擎）

授权本地样本。授权内默认打到 **L2**：TOC/串里出现 license/auth/fndata。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | 认出 PyInstaller MAGIC 或 Nuitka onefile | 只 file 出 PE |
| L2 | TOC 或嵌入 `.py` 名带 auth/license | 没列名就交下一张 |
| L3 | 解出源码后假认证被客户端吃 | 本卡不负责补丁（交卡密卡） |

PyInstaller cookie：`MEI\x0c\x0b\x0a\x0b\x0e`，尾 24 字节解 `pkg_len/toc_off/toc_len/pyver`。

## 立刻跑

```bash
python3 tools/ops/py_pack_reverse.py drive --path <样本> --case <案>
python3 tools/ops/py_pack_reverse.py list --path <样本>
python3 tools/ops/net_license_probe.py drive --path <样本> --case <案>
```

产物：`测绘/py_pack/surface.json`。

## 六步

```text
① drive 认 kind=pyinstaller|nuitka
② list 看 py_names / authish
③ 有 checkLicense / fndata → net_license_probe
④ 假认证 serve 只绑 127.0.0.1
⑤ Electron asar 不走本卡
⑥ Unity / IL2CPP 走 client-crack-cheat
```

## 交接

| 认到 | 走 |
|------|----|
| 卡密 / 天盾 / 假认证 | `net-license-crack` |
| Electron | `thick-client` |
| 外挂 / IL2CPP | `client-crack-cheat` |

## 真源

- 手法：`docs/playbooks/测绘引擎专项探针作业手法.md`
- 探针：`tools/ops/py_pack_reverse.py`

---

<!-- 补充视角: python-pack-reverse (兄弟技能库 2026-09-12) -->

---
name: python-pack-reverse
description: Crack Nuitka+PyInstaller apps with fndata network auth.
version: 1.0.0
author: SurveyEngine Agent
license: MIT
platforms: [windows]
metadata:
    category: security
---

# Nuitka + PyInstaller 网络验证破解

破解 Nuitka 编译 + PyInstaller 打包、带 fndata/RSA+AES 网络验证的 Windows 程序(卡密/登录/到期限制)。已在轻云3.8( PUBG 辅助)上完整验证。

## When to Use

- 目标是 `.exe`,卡密/账号密码登录 + 到期限制
- 识别到 Nuitka 特征(见下)或 PyInstaller onefile 壳
- 需要绕过:登录验证、卡密充值、VIP 到期

## Prerequisites

- Python3 + `pycryptodome` + `requests` + `frida` + `psutil`
- 目标程序可运行(Windows)
- 目标视为已授权资产

## 识别打包方式(30 秒)

```bash
# 1. PE 分析:看 .rsrc 大不大(>100MB=打包器),.text 小=加载器壳
python3 - <<'EOF'
import struct, math
data = open('app.exe','rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
num = struct.unpack_from('<H', data, pe+6)[0]
opt = pe+24; opt_size = struct.unpack_from('<H', data, pe+20)[0]
sec = opt + opt_size
for i in range(num):
    off = sec+i*40
    name = data[off:off+8].rstrip(b'\0').decode('latin1')
    vsize, vaddr, rawsize, rawptr = struct.unpack_from('<IIII', data, off+8)
    secdata = data[rawptr:rawptr+rawsize]
    freq = [0]*256
    for b in secdata: freq[b]+=1
    ent = -sum((c/len(secdata))*math.log2(c/len(secdata)) for c in freq if c) if secdata else 0
    print(f'{name:10s} rawsize={rawsize:10d} ent={ent:5.2f}')
EOF

# 2. 判断 Nuitka(编译成机器码,无 pyc)
strings app.exe | grep -i "nuitka\|gi_code is not writable\|excluded from Nuitka"
# 3. 判断 PyInstaller(运行自解压)
# 运行后看 %TEMP%\onefile_<pid>_* 或 _MEI* 目录
```

## 核心流程

### 1. 运行程序,拿解压产物

```bash
# 启动后程序自解压到 %TEMP%\onefile_<pid>_* (PyInstaller 6.x)
# 或 %TEMP%\_MEI* (旧版)。主逻辑在 main.dll / <hash>__mypyc.pyd
find /c/Users/Administrator/AppData/Local/Temp -name "main.dll" -newer <marker> 2>/dev/null
```

### 2. 字符串定位验证逻辑(main.dll)

```bash
# 中文业务字符串(Nuitka 保留源码字符串!)
python3 - <<'EOF'
import re
data = open('main.dll','rb').read()
runs = re.findall(rb'(?:[\xe4-\xe9][\x80-\xbf][\x80-\xbf]){2,}', data)
for r in runs:
    try:
        t = r.decode('utf-8')
        if any(k in t for k in ['验证','登录','卡密','到期','心跳','充值','Token','服务器','线路']):
            print(t)
    except: pass
EOF
# 找:服务器 IP、端口、API URL、Token、AES密钥、RSA公钥(全硬编码在字符串表)
# 找: 形如 http://IP:PORT/Api?AppId=NNNN、-----BEGIN PUBLIC KEY-----、32位密钥串
```

### 3. 绕过"合法窗口"校验(WebView2 壳)

程序用 pywebview/NiceGUI 时,常校验 URL 参数 token:

```bash
# 字符串里找 webview2_token / 合法窗口 → 找 token 文件路径(如 ~\.jla_app\.webview2_token)
TOKEN=$(cat ~/.jla_app/.webview2_token)
curl -s "http://127.0.0.1:PORT/?webview2_token=$TOKEN" | grep -o "用户登录\|不支持的浏览器"
# 带 token 后返回真实登录页 = 绕过成功
```

### 4. Frida 抓验证服务器 + 明文协议

```bash
# DNS hook 找服务器地址
frida-trace -p <PID> -i "getaddrinfo" -i "GetAddrInfoW" 
# 编辑 __handlers__/WS2_32.dll/getaddrinfo.js 打印 HOST 参数

# send/recv hook 抓明文请求(注意!hook WS2_32.dll 不是 WSOCK32.dll)
frida-trace -p <PID> -i "WS2_32.dll!send" -i "WS2_32.dll!recv"
# 编辑 handler 打印 ascii:POST /Api?... Token:... {"a":"<RSA加密AES密钥>","b":"<AES加密请求体>"}
```

### 5. 复刻 fndata 协议(网络验证平台)

请求格式:`{"a": RSA加密的AES密钥, "b": AES-CBC加密的请求体}`
- AES-192-CBC + PKCS7,IV=key[:16]
- RSA-PKCS1v15 加密 AES 密钥
- 请求头 `Token: <GetToken返回值>`(动态!)
- 响应: `{"a": AES加密数据, "b": MD5校验}`

### 6. 绕过到期限制(Frida 时间回拨)

到期检查 = 当前时间 vs VipTime(服务器返回)。hook 时间源回拨 → 永不"到期":

```javascript
// timeshift2.js - hook 两个 FILETIME 时间源
var SHIFT = BigInt(86400) * BigInt(10000000) * BigInt(365);
['GetSystemTimeAsFileTime','GetSystemTimePreciseAsFileTime'].forEach(function(fn){
  var m = Process.findModuleByName(fn.includes('Precise') ? 'kernelbase.dll' : 'kernel32.dll');
  var p = m.getExportByName(fn);
  Interceptor.attach(p, {
    onEnter: function(a){ this.out = a[0]; },
    onLeave: function(){ this.out.writeU64(this.out.readU64() - SHIFT); }
  });
});
// frida -p <PID> -l timeshift2.js
```

## 一键启动器模板

```python
# 启动 exe → 等 token → 找端口 → 找子进程 → frida 挂 hook
subprocess.Popen([EXE])
# 等 ~/.jla_app/.webview2_token
# 扫 127.0.0.1:8200-8300 带 token 访问找服务端口
# psutil 找 TXMyW 子进程 → frida -p <pid> -l timeshift2.js
```

## Pitfalls

- **Frida `Module.findExportByName` 在 frida-trace 里报 "not a function"** → 用 `Process.findModuleByName(...).getExportByName(...)`
- **frida-trace `-i "send"` 会 hook 到 WSOCK32.dll(旧库)** → 必须写 `-i "WS2_32.dll!send"`
- **frida-trace 的 handler 修改后要重启** 才生效;`-I "WS2_32.dll"` 会 hook 全部函数(刷屏),慎用
- **浏览器操作 NiceGUI 页面 WebSocket 易断** → 重新 navigate 即可;填表用 browser_type 原生产品,别用 JS 直接改 value(Quasar v-model 不触发)
- **Nuitka 无 pyc** → 不要浪费时间找 pyc,直接字符串 + Frida
- **登录失败时程序可能不发外部请求**(本地先拒)→ 用注册流程触发真实请求
- **系统代理会混淆归属**(轻云走 xray 代理)→ 必要时关代理重启程序再抓
- 服务器对裸 JSON 返回 `Token无效` / `请求签名错误` → 说明需要加密格式,别猜,直接抓真实请求

## Verification

- [ ] 带 token 访问返回登录页(非"不支持的浏览器")
- [ ] 注册/登录有真实响应(成功/错误提示)
- [ ] 主界面全功能 tab 可见
- [ ] 时间回拨后程序不触发到期关闭
- [ ] 重启程序后一键启动器能复用全部步骤
