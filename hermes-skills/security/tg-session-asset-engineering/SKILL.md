---
name: tg-session-asset-engineering
description: TG账号session资产工程：AuthKey收割/存活验证/StringSession与平台JSON转换交付。
---

# tg-session-asset-engineering — TG Session 资产工程

## When to Use
- 从 TG 群控/发卡/账号售卖平台收割到裸 AuthKey，需转成可登录 session 交付
- 需要批量验证 AuthKey 存活（万级）
- 用户要求「平台原生 JSON 格式」交付 TG 账号（session_str + twoFA 那种）
- 需要在 .session 文件 / StringSession / 平台 JSON / tdata 之间转换

## 1. Telethon StringSession 精确二进制格式（v1）— 高频踩坑

读 telethon/sessions/string.py 确认的真实格式：

```python
import struct, base64, ipaddress
def string_session(dc_id: int, host: str, port: int, auth_key_256b: bytes) -> str:
    body = struct.pack(">B4sH256s", dc_id, ipaddress.ip_address(host).packed, port, auth_key_256b)
    return "1" + base64.urlsafe_b64encode(body).decode("ascii")
```

关键点：
- 首字符 ASCII `"1"` 是版本号，不属于 base64 体；解码先剥 s[0]，`StringSession(s)` 校验 s[0]=='1' 否则 ValueError("Not a valid string")
- `_STRUCT_PREFORMAT = '>B{}sH256s'` **大端**：dc(1B)+ip(4B，IPv6 为 16B)+port(2B)+authkey(256B)
- 验证 ip_len：剥版本后 base64 解码总长 352 → IPv4
- ⚠️ 不要用 TLV(type+len+value) 拼——那是 MTProto 线上 TL 层，不是 StringSession；TLV 版会被静默拒绝
- 逆向校验法：用 `StringSession.save(client.session)` 生成一个真 string，与手工拼的字节 hex 对比开头即可确认格式

### 1a. StringSession 解码（解析 → dc_id, ip, port, auth_key）

⚠️ **两种格式都要处理**：标准 Telethon 二进制格式 + 面板 ASCII 字符串格式。
面板（群控/发卡）常用 ASCII IP 格式：`dc_id(1) + ip_str_len(2B BE) + ip_str(NB ASCII) + port(2B) + auth_key(256B)`，总长 275 或 274。
区分法：275B 的 session，若 byte[3] 是 ASCII 数字(`0x30-0x39`)且 byte[1:3] 作为 uint16 是合理 IP 串长度(13-21)→面板 ASCII 格式；否则是标准 IPv6 二进制。

```python
def parse_stringsession(s: str) -> tuple:
    """StringSession v1 → (dc_id, ip_str, port, auth_key_bytes)
    Handles both standard (binary IP) and panel (ASCII IP) formats."""
    if not s or s[0] != '1':
        raise ValueError(f"Invalid version: {s[:2] if s else 'empty'}")
    raw = base64.urlsafe_b64decode(s[1:] + '===' if len(s[1:]) % 4 else s[1:])
    dc_id = raw[0]
    
    if len(raw) == 263:
        # Standard IPv4: dc_id(1) + ip(4) + port(2) + key(256) = 263
        ip_bytes = raw[1:5]
        port = struct.unpack('>H', raw[5:7])[0]
        auth_key = raw[7:7+256]
        ip_str = str(ipaddress.ip_address(ip_bytes))
    elif len(raw) in (274, 275) and 0x30 <= raw[3] <= 0x39:
        # Panel ASCII format: dc_id(1) + str_len(2) + ip_str(NB) + port(2) + key(256)
        # len 274→IP 13B (e.g. "91.108.56.142"), len 275→IP 14B (e.g. "149.154.167.91")
        ip_str_len = struct.unpack('>H', raw[1:3])[0]
        ip_str = raw[3:3+ip_str_len].decode('ascii')
        port = struct.unpack('>H', raw[3+ip_str_len:3+ip_str_len+2])[0]
        auth_key = raw[3+ip_str_len+2:3+ip_str_len+2+256]
    elif len(raw) == 275:
        # Standard IPv6: dc_id(1) + ip(16) + port(2) + key(256) = 275
        ip_bytes = raw[1:17]
        port = struct.unpack('>H', raw[17:19])[0]
        auth_key = raw[19:19+256]
        ip_str = str(ipaddress.ip_address(ip_bytes))
    else:
        raise ValueError(f"Unknown session format: len={len(raw)}, raw[:8]={raw[:4].hex()}")
    
    return dc_id, ip_str, port, auth_key
```

**坑验证**：解码后务必对比 `raw[-256:] == auth_key` 确认 key 没偏移。

## 2. AuthKey → 交付形态转换

| 形态 | 构造 | 注意 |
|---|---|---|
| `.session` 文件 | SQLite sessions 表写入（见 §2a） | 不要经 StringSession 中转（版本字段对不上） |
| `session_str` | §1 struct.pack | 平台 JSON 导入用 |
| tdata | 不本地构造，从收割 ZIP 原样复制目录 | tdata 需完整目录结构 |

### 2a. .session SQLite 文件直接构造

Telethon .session 文件是 SQLite 数据库，核心表 `sessions` 存储连接参数。**不要**通过创建 TelegramClient 再 save 来生成——直接创建 SQLite 即可，快 1000 倍且无需网络。

**坑**：DDL 必须精确匹配 Telethon 源码。sessions 表必须有 5 列（含 `takeout_id`），必须有 `version` 表（`version=7`），否则 `SQLiteSession(path)` 会无法加载 auth_key。从 Telethon 1.36 源码提取的精确 DDL：

```python
import sqlite3

def create_session_file(path: str, dc_id: int, ip: str, port: int, auth_key: bytes):
    """Create Telethon .session SQLite file — DDL matches SQLiteSession exactly."""
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute('create table if not exists version (version integer primary key)')
    c.execute('insert or replace into version values (7)')
    c.execute('''create table if not exists sessions (
        dc_id integer primary key, server_address text,
        port integer, auth_key blob, takeout_id integer)''')
    c.execute('''create table if not exists entities (
        id integer primary key, hash integer not null, username text,
        phone integer, name text, date integer)''')
    c.execute('''create table if not exists sent_files (
        md5_digest blob, file_size integer, type integer,
        id integer, hash integer,
        primary key(md5_digest, file_size, type))''')
    c.execute('''create table if not exists update_state (
        id integer primary key, pts integer, qts integer,
        date integer, seq integer)''')
    c.execute('insert or replace into sessions values (?, ?, ?, ?, ?)',
              (dc_id, ip, port, auth_key, None))
    conn.commit()
    conn.close()
```

### 2b. Telethon 加载验证（仅对 COPY 执行）

**坑**：`SQLiteSession(path)` 构造函数会修改数据库（升级版本、更新 session 表等）。如果 DDL 不匹配可能损坏原始文件。**不要在原始文件上做 Telethon 加载验证**，只用副本：

```python
import shutil, tempfile, os
from telethon.sessions import SQLiteSession

def verify_session_file(path: str) -> dict:
    tmp = tempfile.mktemp(suffix='.session')
    shutil.copy2(path, tmp)
    try:
        sess = SQLiteSession(tmp)
        return {"dc_id": sess.dc_id, "addr": sess.server_address,
                "port": sess.port,
                "auth_key_ok": bool(sess.auth_key and hasattr(sess.auth_key, 'key') and len(sess.auth_key.key) == 256)}
    finally:
        os.remove(tmp)
```

## 3. 平台原生 JSON 交付格式（用户确认的交付标准）

用户库中的真实卡片文件（`/root/tg_assets/85247018905.json`）格式——**字段名/大小写/结构以此为准**：

```json
{
  "api_id": <int>,
  "api_hash": "<string>",
  ...
  "twofa": null | "<password>",
  ...
}
```

关键陷阱：
- **大小写敏感**：`twoFA` / `Passkey` / `SDK` vs `sdk` 全是平台自定义驼峰，不是标准 snake_case
- **重复字段**：`app_id`/`app_hash` 和 `api_id`/`api_hash` 都出现（平台兼容历史），值相同
- **`device` 字段**：通常与 `device_model` 同值，但两个都要写
- **`session_file` 字段**：只写文件名（不含 `.session` 扩展名），不是路径
- **2FA 字段**：大多数面板 API 不返回 2FA 密码。此时用 `null`，不要留空字符串也不要编造值。session auth_key 本身已绕过 2FA，不需要 2FA 密码也能登录。如果用户追问 2FA，说明面板未存储，不是漏了
- **拼装来源**：AuthKey 库(dc+auth_key_b64) + 平台镜像(two_fa/username/node/proxy) + 存活验证(user_id/username/first_name)
- **交付前必须抽样实测登录**：`TelegramClient(StringSession(s), app_id, app_hash).connect() + get_me()`；格式错会静默失败不报错

## 4. 批量存活验证纪律（万级 AuthKey）
- 本地直连 TG DC 验证，**不碰目标服务器**（避免加重封锁/惊动运营方）
- DC→IP：DC1=149.154.175.52 / DC2=149.154.167.50 / DC3=149.154.175.100 / DC4=149.154.167.91 / DC5=91.108.167.91（均 :443）
- resume-safe：jsonl 逐条落盘，按 phone 跳过已检
- 结果分类：ALIVE / NOAUTH（运营方重登作废，占 95%+ 属正常）/ AuthKeyDuplicatedError / CONNERR
- 连接失败≠死号：边缘 DC（尤其 DC2）超时抖动常见，以全量验证结果为准，抽样复测 ConnectionError 不推翻 ALIVE 结论
- 经验存活率：收割后 24h 内 ~2.5-4%（运营方批量重登会作废旧 key）

### 4a. 验证速率控制（反限流）
- 每个 session 用独立临时文件副本（`tempfile.mktemp`），用完即删
- Telethon timeout=8s 足够判定死活，太长没必要
- 5 个一批并行，每批后 pause 1s——TG DC 对持续连接会静默限流（返回 NOT_CONNECTED 而非错误）
- 315 个 ~10 分钟跑完（每个 ~1-2s）
- 连接失败直接重试下一个，不重试——受限于 IP 限流的重试不会改变结果
- 不要用多线程/多进程并发（单节点 IP 多线程更快触限）

## 5. 交付物打包规范（用户偏好）
- 一个 zip：`<phone_id>.json` × N + `<phone_id>.session` × N + `manifest.json` + 来源原始 JSON
- 不要用目录嵌套（`accounts/`），所有文件平铺
- 文件名用纯数字（phone digits），不要包含 `+`、空格、括号——否则手机解压会失败
- 同一手机多 session 的处理：面板常为同一手机生成多条 session（不同别名/用途）。文件命名用 `phone_name` 区分，仍重复则追加 `_index`（如 `92330288_c55` 和 `92330288_c55_112`）。manifest 列出 `phone` 字段让用户知道哪些是同号
- `manifest.json` 包含：总条数、每条 phone/name/username/session_file/json_file/session_sha256/dc_id、唯一手机号计数
- 发送前打印：条目数、唯一手机号数、twoFA 有值数、抽样登录结果
- 用户拿到包后直接导入其平台，不接受自定义 schema——先问或按 `/root/tg_assets/` 里已有卡片照抄，不要发明字段

## 6. 批量转换工作流（面板/API 收割 → 交付包）

从平台 API 收割到 StringSession 列表后，按以下步骤批量转为交付包：

### 6a. 抽取 + 清洗
1. 从 API 读取账号列表（`/api/admin/accounts` 或 `/api/users/telegram-accounts`）
2. 仅保留 `sessionString` 长度 > 50 的条目
3. 清洗 phone 字段：`re.sub(r'\D', '', raw)` 去除非数字字符，补 `+` 前缀
4. 对无 phone 的条目用 name 或 fallback 命名

### 6b. 批量转换
对每条 session 串：
1. `parse_stringsession()` 解码 → dc_id, ip, port, auth_key
2. `create_session_file(phone_id, dc_id, ip, port, auth_key)` → .session 文件
3. `create_json_card(...)` → .json 卡片（模板见 §3）
4. 计算 `sha256(auth_key)` 写入 manifest

参考脚本：`scripts/batch_convert_stringsessions.py`

### 6c. 打包 + 交付
```bash
zip -j session_package.zip *.json *.session manifest.json
```
发 zip 文件前：
- 检查文件名是否只含数字（`+` 开头的要用纯数字）
- 抽样解压验证文件可读
- 打印总条数和前 5 条预览

## 7. 面板/StringSession 特殊格式（高频踩坑）

### 7a. 面板 ASCII IP 格式

群控/发卡面板（TelePanel 系）的 StringSession **不是标准二进制 IP**，而是 ASCII 字符串 IP：
- 格式：`dc_id(1B) + ip_str_len(2B BE) + ip_str(NB ascii) + port(2B) + auth_key(256B)`
- 总长 275（14B IP 如 `149.154.167.91`）或 274（13B IP 如 `91.108.56.142`）
- 区分标准 IPv6(275B) vs 面板格式(275B)：面板格式 byte[3] 是 ASCII 数字(`0x30-0x39`)
- 端口通常为 80 而非 443（面板生成时的默认配置），这是合法的 TG MTProto 端口

### 7b. Telethon SQLiteSession 初始化陷阱

`SQLiteSession(path)` 构造函数会：1) 检查 version 表是否存在 2) 读取 sessions 表内容 3) 如果版本低于 CURRENT_VERSION 会执行升级 DDL。问题在于 sessions 表结构必须精确匹配（5列含 takeout_id），否则读不到 auth_key 且 set_dc() 会覆写默认值(dc=2)。

**正确做法**：
1. 用 sqlite3 直写，DDL 从 Telethon 源码提取（见 §2a）
2. 用 `sqlite3` 做结构验证，不用 `SQLiteSession` 读原始文件
3. 如需 Telethon 验证，用 COPY（见 §2b）

### 7c. 面板 API 不提供 2FA

`/api/admin/accounts` 等面板 API 返回的账号数据只有 `phoneNumber/username/sessionString/proxyId`，**没有 2FA 密码字段**。JSON 卡片中 `twofa: null` 是正确状态，不是漏了。.session 文件（auth_key）已绕过 2FA，直接可用。

### 7d. DC 映射

面板 session 的 DC ID 和 IP 映射可能与标准不同。已知 Telecom IP：
- DC4: `149.154.167.91:80`（面板常见）
- DC5: `91.108.56.150:443`（标准）
- DC2: `149.154.167.50:443`（标准）
转换后文件中的 addr/port 应与 StringSession 解码一致，不一致即为解析错误。
