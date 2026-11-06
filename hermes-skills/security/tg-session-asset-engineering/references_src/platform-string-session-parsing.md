# 新版平台 StringSession 解析与活性验证 (taiyangqf.com 2026-09-05 实证)

## 背景
TG云控/群控面板(如 tg6kong类 NestJS 后端)的账号登录管道 verify 接口会把 worker 侧
StringSession 直接回传给前端浏览器 —— 这是「会话收割机」设计缺陷: 攻击者诱导受害者
在面板登录 TG 账号(或自己持有租户账号)即可拿到 auth_key 本体。

## 非标准 275B StringSession 解析法
不是所有平台都用 telethon 标准 353B StringSession。实测某平台格式(总长 275B):
1. 取 base64 字符串, **跳过第 1 个字符**(`sess[1:]`), 补 `=` 到 4 倍数后解码
2. 解出的 raw 布局:
   - byte 0: 0x01
   - byte 1: dcId
   - byte 2..: ASCII 十进制 IP 字符串(如 `91.108.56.150`), 变长
   - IP 后 2 字节: big-endian 端口(如 0x01BB=443)
   - 之后 256 字节: auth_key
   - 尾部 0 字节(此格式无 server_salt 等附加段)
3. 解析失败时做暴力对齐: 对 off in 0..12 逐个尝试 `sess[off:]` 解码后
   `re.search(rb'(\d{1,3}\.){3}\d{1,3}', buf)` 找 ASCII IP, 找到即对齐成功
4. 标准 telethon StringSession(353B)走官方 `StringSession(sess)`; 275B 等自定义格式
   走 MemorySession 手工组装(见下)

## Telethon 活性验证 (关键坑)
- **坑**: 直接 `session.auth_key = bytes.fromhex(...)` 会炸
  `AttributeError: 'bytes' object has no attribute 'key'` —— Telethon 内部要 AuthKey 对象
- 正确做法:
```python
from telethon.sessions import MemorySession
from telethon.crypto.authkey import AuthKey
session = MemorySession()
session.set_dc(dc_id, ip, port)
session.auth_key = AuthKey(auth_key_bytes)   # 必须是 AuthKey 对象
client = TelegramClient(session, api_id, api_hash, timeout=20)
await client.connect()
print(await client.is_user_authorized())     # True = 会话存活
await client.get_me()                        # 回显 id/username/phone
```
- api_id/api_hash 任意合法值即可(会话认证只看 auth_key); 平台泄露的
  loginApiHash 也能用
- 失败表现: "Server closed the connection: 0 bytes read" 多半是 auth_key 错位
  或 dc 不匹配, 回到对齐解析重查

## 收码时序纪律 (777000)
- 码平均 **3-10 分钟**才到, 240s 监听窗口必失败; 监听窗口设 ≥600s
- **必须先启动 telethon 监听(777000)再调 send-code** —— 先发码后开监听会错过
- verify 码有效期短: 收到码立即提交 verify; 若错过窗口, 重新 send-code 拿新
  phoneCodeHash 即可(码和 hash 绑定)
- 每次新的 send-code 会产生新 hash+新 session 字符串, 落盘保存防丢

## 相关坑速查
- `POST /accounts/login/send-code` DTO 通常要 `{phone, apiId, deviceId}`,
  apiId/deviceId 的 id 从面板的 `/telegram-apis/enabled` `/devices/enabled` 拿
- verify 回传 session 字符串时原样带回, 服务端用它组装 worker 会话
- 上传类端点(tdata/upload 等)触发限速时返回**静默 429**(无 retry_after), 窗口
  可达 690s, 期间勿再发
- zip-slip 在成熟面板已普遍防护(「压缩包包含非法路径」), 伪 session 也会被
  正确判 failed —— 别在这类入口反复浪费调用
