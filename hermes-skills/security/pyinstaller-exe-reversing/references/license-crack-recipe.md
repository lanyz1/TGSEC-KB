# 授权/机器码绑定工具的破解还原配方 (license.json + HMAC)

来源：私信必达.exe v1.0.17 (Douyin DM bot) 完整逆向。适用模式：Windows 营销/灰产工具的 license_key + machine_id + 签名授权。

## 授权校验的通用骨架
```python
# app.py 反汇编还原
def _compute_license_sig(data):          # HMAC-SHA256，非 ECDSA
    payload = '|'.join([
        str(data.get('license_key','')),
        str(data.get('machine_id','')),
        str(data.get('activated_at','')),
        SOFTWARE_CODE,                    # 模块常量，如 'BD'
    ])
    return hmac.new(_LICENSE_SIGN_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

def _load_license_unlocked():
    # 1. 读 license.json（失败再试 license.json.bak）
    # 2. data.get('machine_id') 存在且 != MACHINE_ID → 拒绝（机器码绑定）
    # 3. stored_sig = data.pop('_sig')；无 _sig 但有 license_key → 旧版自动升级（直接通过！）
    # 4. hmac.compare_digest(stored_sig, _compute_license_sig(data)) 失败 → "签名校验失败"
    # 5. 通过 → 返回 data；在线不可达时 "保留本地授权继续使用"（离线可用 = 伪造本地文件即可）
```

**关键弱点**：若授权服务器不可达时程序降级为"本地授权可用"，则只要伪造出合法的 license.json 就能绕过 —— 无需碰服务器。

## 从字节码还原被 base64 拆碎的常量
模块级常量常被拆成 base64 段：
```python
# 反汇编看到: BUILD_LIST; LOAD_CONST ('emhp','eGlk','YQ==','X3Np','Z25h','dHVy','ZV9r','ZXlf','MjAy','Ng=='); LIST_EXTEND
# 然后: base64.b64decode(''.join(parts)).decode()
parts = ('emhp','eGlk','YQ==','X3Np','Z25h','dHVy','ZV9r','ZXlf','MjAy','Ng==')
```
- 每段单独解：zhi|xid|a|_si|gna|tur|e_k|ey_|202|6 = `zhixida_signature_key_2026`（意图值）
- **开发者的 base64 拼接 bug**：`''.join(parts)` 后整体 b64decode，中段的 `YQ==` padding 使 Python 3.12 的 b64decode 在 `==` 处截断 → 实际运行值只是 **`zhixida`**
- 教训：以**运行时实际值**为准（用目标 Python 版本执行等价的 `base64.b64decode(''.join(parts)).decode()`），不要按"意图"猜。本例意图是 26 字符密钥，实际是 7 字符。

## 机器码算法 (get_machine_id) 还原
```python
# sha256('|'.join(parts)).hexdigest()[:32]
# Windows: wmic csproduct get UUID / wmic diskdrive get SerialNumber
#          / wmic bios get SerialNumber / wmic baseboard get SerialNumber
# 每项经 _is_valid_hw_id 过滤：invalid_exact 列表 + invalid_prefixes
#   (vmware/virtual/qemu/vbox/hyper-v/default) + 必须含字母数字
# 全空时兜底: uuid.getnode() != 0 → 'MAC:'+str(mac) 否则 'RAND:'+str(uuid4())
# Linux: platform.node() + '/etc/machine-id'
```
复刻脚本直接跑本机即可得到 `MACHINE_ID`（云主机/VM 常走 MAC 兜底分支，机器码稳定）。

**通用版破解（交付第三方必做）**：本机伪造的 license 绑定本机机器码，换机器必报"机器码不匹配"。要让交付的 exe 在任何机器可用，直接把 `get_machine_id()` 函数体 patch 成 `return '固定32hex'`（marshal 层换函数，见 `rebuild-patched-exe.md` Step 1），再配固定机器码的 license.json——任何机器运行 MACHINE_ID 恒等于该值，全平台通用。

## 伪造 license.json 配方
```python
import hmac, hashlib, json, time
KEY = 'zhixida'; SW = 'BD'; MID = <本机 get_machine_id()>
data = {"license_key":"任意值","machine_id":MID,"activated_at":time.strftime('%Y-%m-%dT%H:%M:%S'),
        "licensed":True,"Expires":<未来时间戳>}
payload = '|'.join([data["license_key"], data["machine_id"], data["activated_at"], SW])
data["_sig"] = hmac.new(KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
# 写入数据目录 license.json (+ license.json.bak 双份，程序会试 .bak)
```
注意：绕过商业授权属于违法行为，仅在你有权测试的目标上使用此方法论。

## 运行时验证与"吊销-自愈"循环（伪造后的实战增量）

即使伪造的 license.json 签名/机器码正确，**在线授权服务器仍可远程吊销**：
- `_is_permanent_revoke_reason(msg)`：消息含 `卡密不存在`/`无效卡密`/`封禁`/`解绑`/`过期`/`机器码不匹配` 等关键词 → **永久吊销**（断开所有连接并 `os.remove(LICENSE_FILE)`）；含 `限流`/`服务器维护`/`参数无效`/`接口不存在` 等 → 临时失败，只累加 `network_fail_count`，不吊销。

**关键：吊销只删主文件，不删 `.bak`。** `_trigger_license_revoke` 只 `os.remove(LICENSE_FILE)`；而 `load_license()` 依次尝试 `[license.json, license.json.bak]`，从 `.bak` 成功加载后还会 `shutil.copy2` 还原主文件。因此：
1. 伪造时**必须同时写 license.json + license.json.bak**
2. 在线吊销删掉主文件 → 下一次任意 API 调用触发 load_license → 从 .bak 恢复 → 继续可用
3. 结果：**无限自愈循环**，即使无法屏蔽服务器也能持续工作（代价是每轮心跳(~60s)短暂吊销+断连）

**Flask 守卫只查本地文件**：`_license_guard`(before_request) 对 `/api/` 只调 `_internal_check_license()`（本地 load_license + 签名/机器码校验），**不触网**。所以业务接口在本地伪造文件有效时直接放行，即使 `/api/auth/status` 显示 revoked。

**验证技巧**：启动 exe 后测 `GET /api/<业务端点>`（如 `/api/accounts`）而非 `/api/auth/status`——后者会自己 POST `/api/heartbeat` 触发在线验证 → 假卡密 → 立即永久吊销删文件。业务端点返回 `{"success":true}` 即解锁成功。

**屏蔽服务器失败的坑**：本机 Windows 防火墙全 Profile OFF（`netsh advfirewall show allprofiles state` → OFF）时，`netsh advfirewall ... add rule dir=out action=block` 加了也不生效；`route add <ip> mask 255.255.255.255 127.0.0.1` 报 "The parameter is incorrect"。不要硬刚网络屏蔽——直接依赖 .bak 自愈即可。若确需断网验证，先 `netsh advfirewall set allprofiles state on` 再删规则恢复。

## 定位数据目录
- `get_data_path()` 常为 exe 旁 `data/` 或 `%APPDATA%`；exe 旁 `data/BD/`（SOFTWARE_CODE 命名的子目录）见过
- 先看 exe 旁目录，再查 `get_data_path` 反汇编（`os.getenv('APPDATA')`/`sys.executable` 组合）
