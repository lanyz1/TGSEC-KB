<!-- archived from /root/.hermes/skills/security/raw-wire-protocol-probing/SKILL.md on 2026-10-21 -->

---
name: raw-wire-protocol-probing
description: "客户端库拒连老旧服务时用:裸 wire 协议指纹+认证爆破。触发 wire version/SCRAM。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, wire-protocol, mongodb, scram, fingerprint, brute-force, legacy-service]
    related_skills: [network-pentest, middleware-unauth-family, password-cracking, heapdump-credential-hunter]
---

> 归档卡：原目录 `/root/.hermes/skills/security/raw-wire-protocol-probing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/raw-wire-protocol-probing/…')`，不要相对 `references/legacy/` 解析。

# 裸 wire 协议探测与认证测试 (Raw Wire-Protocol Probing)

当一个服务端口开着、但**标准客户端库拒绝连接或根本装不上**时,不要就此写“打不通”。
退化到它自己的二进制 wire protocol:先免认证指纹,再认证爆破。

## 何时用

- 客户端库报**协议代差**而拒连,典型:
  `Server at <IP>:27017 reports wire version 7, but this version of PyMongo requires at least wire version 8`
- 目标环境缺驱动 / 装不上 / 无外网装包 / 只有个裸 socket 可用
- 已知端口开放要指纹服务与版本,但不想搬大依赖
- 旧版数据库/中间件正在被爆破(国内企业内网常见 MongoDB 4.0/4.1)

## 核心规则(先钉死这 4 条)

1. **拒连 ≠ 打不通。** “库版本不兼容”和“网络不通”是两回事。看到 wire/API 版本号就说明 **TCP 已经通了且服务回了话** —— 那是协议代差,退化到裸协议即可。
2. **先跑免认证的那条命令。** 绝大多数 wire 协议都留了一条不需认证的握手/探活命令（MongoDB 的 `isMaster`、Redis 的 `PING`、Memcached 的 `stats`、ES 的 `GET /`），它直接给出**版本、能力位、是否要求认证**。先拿这些再决定要不要爆。
3. **“要求认证”与“未授权”必须分开定论。** 未授权的实例会把真数据直接回给你；回一个**专门的鉴权错误**(如 `command listDatabases requires authentication`)才是“有认证”。两者定级与后续动作完全不同。
4. **长度字段是协议实现里最大的坑，不是最玄的。** 手工构包时 frame 长度/`messageLength` 少算一个尾字节，服务端就把你回成“解析错误”，看起来像“格式/编码错”或“未授权”，**极容易得出假的阴性结论**。先把长度公式写下来再写代码。

## 步骤

### 1. 指纹(免认证)
拿到:`版本` / `协议版本号` / `是否要求认证`。这是后面所有判断的基线。

### 2. 判明认证要求
发那条**应该需要权限**的命令（列出数据/配置的那条）。用返回文案区分:
- 直接回数据/列表 → **未授权**,转数据面
- 回鉴权错误 → **有认证**,进第 3 步
- 回连接被重置 / 无响应 → 可能有**源 IP 白名单**或协议不对（先确认是不是打到了 CDN/反代而不是源站）

### 3. 认证爆破
- “用户名存在性与否”如果行为可区分，就**先枚举用户名再爆口令**，把笛卡尔积砍成一个维度（对象存储场景见 `object-storage-takeover-mining` 的 AK oracle；各类协议同理）
- **限速与锁定**先测：连发几次看是否回锁定/退避文案。锁定后不要硬刚，换源 IP 或等窗口
- **实现正确性的自检信号**：如果服务端把你走到了“凭据错”这一步（而非解析/协议错），说明你的加密/签名实现是**对的**，只是凭据不对 —— 继续换字典，不要回头改代码

### 4. 落盘
`python3 -u` + 重定向到文件 + 后台跑。否则缓冲会把输出吞掉，看起来像“跑完了没结果”。

## 已实现：MongoDB(wire version ≤7，即 MongoDB ≤4.1)

pymongo 4.x 硬性要求 wire version ≥8，MongoDB 4.0/4.1 **直接拒连**。
直接用 `scripts/mongo_scram_client.py`（裸 socket + 自写 BSON 编解码 + SCRAM-SHA-1/256）。

**三条命令的逐层判据**:
| 发什么 | 要不要认证 | 证明了什么 |
|---|---|---|
| OP_MSG(opCode 2013) + `{"isMaster":1,"$db":"admin"}` | **不要** | `maxWireVersion`/`maxBsonObjectSize`/`readOnly` → 版本 + 确是该口 |
| `{"listDatabases":1,"$db":"admin"}` | 要 | 回库列表 = 未授权;回 `command listDatabases requires authentication` = 有认证 |
| SCRAM `saslStart`→`saslContinue` | 要 | 走到 `Authentication failed.` = 实现正确、凭据不对 |

**OP_MSG 长度公式(踩过)**：`messageLength = 16(header) + 4(flagBits) + 1(kind=0) + len(BSON)`。
少算那 5 字节 → 服务端回 `invalid bson in element with field name 'isMaster'`，**别把它读成“编码错”或“不可用”**。

**SCRAM 要点**:
- `SaltedPassword = PBKDF2-HMAC(password, salt, iterations, dklen)`，SHA-1 → dklen 20，SHA-256 → dklen 32
- **SCRAM-SHA-256 要先把口令 `sha256(hex)` 再进 PBKDF2**（与 SHA-1 步骤不同）
- `ClientKey = HMAC(SaltedPassword, "Client Key")`；`StoredKey = H(ClientKey)`
- `AuthMessage = clientFirstBare + "," + serverFirst + "," + clientFinalWithoutProof`
- `ClientProof = ClientKey XOR HMAC(StoredKey, AuthMessage)`
- BSON 解码需支持 `0x05` binary（salt 是 binary）、`0x01` double（响应里 `ok` 是 double，不是 int）

## Pitfalls

- **把“库不兼容”写成“目标不可达”** —— 报错里带 wire/API 版本号就是已经通讯上了。先尝试裸协议再下结论。
- **长度/帧字段算错 → 假的“未授权”结论**。先用一条必然成功的命令（`isMaster`）验证你的编解码器，再去跑那些需要认证的命令。
- **只看端口开放就判“未授权”** —— 一定要把“应该需要权限的那条命令”真发出去看返回。
- **拿一个已回“凭据错”的实现回头改代码** —— 那是实现正确的信号，时间应该花在字典上。
- **爆破不带退避/不测锁定** —— 被锁后继续打会把自己焊在门外（青龙类面板指数退避能到几十小时）。
- **同段多台同名服务凭据不通用** —— AK/用户名重名而密钥各异，逐台独立验证。

## 交付物

- 指纹结果（版本 / 协议版本 / 是否需认证）
- 能力矩阵：未认证可做什么 / 认证后可做什么（逐项附命令与返回）
- 凭据命中情况（**报告里一律 [REDACTED]**，只写存在性与验证方式）
- 可跑脚本：`scripts/mongo_scram_client.py`

## 关联

- `middleware-unauth-family`：**同一领域的用户自有技能**，其“MongoDB 未授权”一节只给了 pymongo 一行命令，对 MongoDB ≤4.1 会直接报 wire version 拒连；遇到旧版实例按本技能的裸协议路径走。建议 `hermes curator adopt middleware-unauth-family` 后由 curator 把两者合并
- `object-storage-takeover-mining`：AK/用户名存在性 oracle 与逐台独立验证思路同源
- `network-pentest`：上游的端口扫描 / 服务枚举环节
- `password-cracking`：拿到哈希之后的离线阶段
- `heapdump-credential-hunter`：拿到可复用连接串的上游来源
