---
name: c2-zero-trust-console
description: >-
  打授权目标上的 C2 零信任控制台：nftables 黑洞、两步 API 敲门、CF 仅回源、
  时间窗 HMAC / SPAKE2、Vue Console / PTY 8889 / WebRTC H.264、内存沙箱。
  触发：C2 控制台、零信任敲门、端口敲门、黑洞模式、nftables DROP、SPAKE2、
  HMAC 控制台、Vue C2、PTY 8889、内存沙箱控制台。
  不是 host-c2-verify（那是授权机上验我们自己的 Sliver 落地）。
  支付假付、彩虹易 return_url 不并进本卡。
---

# C2 零信任控制台（测绘引擎）

目标须在 `config/scope*.json`。这是 **打别人家（已授权）C2 设施**，不是本机 implant 回连。  
授权内默认打到 **L2**：控制台 / 终端 / 库 三选一可验证。  
先问只剩：改原超管密、持久化清日志、耗余额。

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | CF 前置 + 重点口黑洞/假 OPEN；JS 里有 knock/HMAC/wss/ICE 词 | 只扫 health；只写「主机不在线」 |
| L2 | JS 抽出敲门序列或 HMAC 钥，**或** 源站 Host/XFF 出控制台，**或** 未授权 JSON（keys/db/pty） | 65535 空转；TCP 全通但 HTTP 同码当真开 |
| L3 | 授权内进 Console / PTY / 库查询，证据打码 | 默认改超管密；把彩虹易 F-01 当本链洞 |

## 立刻跑

```bash
# 认面：CF / JS 敲门 / HMAC / 控制台路径；不默认喷 65535
python3 tools/ops/c2_zt_probe.py drive --base https://授权站 --case <案>

# 已有候选源站 IP（先 origin_recon / cert-origin，IP 须进 scope）
python3 tools/ops/c2_zt_probe.py drive --base https://授权站 --origin-ip <源IP> --case <案>

# JS 离线抽
python3 tools/ops/c2_zt_probe.py extract --path bundle.js

# 铸时间窗 HMAC（抓到钥再打）
python3 tools/ops/c2_zt_probe.py hmac --key <钥> --method GET --path /api/knock

# 只在抽出序列后才敲门，再回看重点口
python3 tools/ops/c2_zt_probe.py knock --host <源IP> --seq 7000,8000,9000 --proto tcp
```

产物：`测绘/c2_zt/surface.json`。

溯源并行（本卡不替代）：

```bash
python3 tools/ops/origin_recon.py --domain 授权域 --case <案>
python3 tools/ops/js_secret_hunter.py hunt --base https://授权站 --case <案>
python3 tools/ops/trusted_ip_header_probe.py --base https://授权站 --case <案>
```

## 六步（禁止停在「全端口无响应」）

```text
① CDN/证书找源 IP → Host / XFF 验是不是还黑洞
② 拉 Vue/Worker JS：knock 序列、HMAC 钥、wss PTY、STUN/TURN、backaddress
③ 有序列才 knock；无序列不要扫 1–65535
④ 铸 X-Auth 短窗重放；爆破不超过短字典，先找泄露
⑤ 控制台路径：/api/v1/keys/apply /pty/ /api/db/query /api/sandbox/exec
⑥ L2 填对象矩阵「自己×读」。改密/持久化先问。沙箱逃逸交接 linux-post-exploit / container-security-testing
```

## 交接

| 认到 | 走 |
|------|----|
| 只要源站 IP / 证书 SAN | `cdn-origin-tracing` · `origin_recon.py`，验完回本卡 `--origin-ip` |
| 只是 XFF 把 403 打成 200 | `trusted-ip-header`（加款仍走 hardcoded-token-cfip-fund） |
| PTY `wss://` 消息/CSWSH | `websocket-pentest` · `ws_probe.py` |
| 内存沙箱 / gvisor / runc | `linux-post-exploit` · `container-security-testing` · `容器逃逸手法.md` |
| 授权机验我们自己的 Sliver | `host-c2-verify` · `host_c2_verify.py` |
| 支付 notify / return_url | 假支付专卡，不并本链 |

## 强制

1. 点名敲门 / 黑洞 / Vue C2 **先开本卡**，不要并进 `host-c2-verify`。
2. 授权内出 HMAC 重放 / 源站 Host 旁路 / 未授权 JSON **直接做**，不要只交架构图。
3. TCP 全开且 HTTP 同码 = TUN 假 OPEN，禁止报 L2。
4. 彩虹易弱校验、默认改超管密、广谱 65535 不作为本卡结案。

## 真源

- 手法：`docs/playbooks/Go后端零信任敲门与黑洞模式手法.md`
- 探针：`tools/ops/c2_zt_probe.py`

---

<!-- 补充视角: c2-zero-trust-console (兄弟技能库 2026-09-12) -->


# C2 零信任框架攻击 — 完整攻击路径

针对「黑洞模式(端口全DROP) + 端口敲门 + CDN前置(CF) + HMAC签名 + Vue C2 Console + 内存沙箱」特征的高价值 C2 设施。
**核心判断**: 任何能拿到「控制台/终端/数据库/SSH」其中之一的路径都是目标。这不是普通 Web 站。

> 融合来源: C2零信任攻击流程手册 + cloudflare-bypass + server-getshell-playbook + TGSEC 方法论 + 空间测绘引擎侦察

---

## 〇、目标架构拆解(先画攻击面地图)

```
外部扫描器 → nftables(全局 DROP)← 黑洞, 扫描=全关
├── :22 SSH        → 默认禁止(敲门后开?)
├── :8888 探针     → DROP(敲门用?)
└── :8080 Web登录  → 仅 Cloudflare 代理(直连=403, CF 回源可打)

已鉴权操作员:
  敲门(2步API握手) → CF CDN(0RTT) → CF校验Host+时间戳+HMAC令牌
  → 操作员IP → SSH(1234) → PTY(8889 Web控制台API) → Vue C2 Console

Go Backend:
  nftables WAF(白名单+CC) → 动态白名单(timeout) → 内存资产加载
  → 控制台HTML/app.js/核心Bundle → 内存沙箱(无痕执行)

Vue Console: H.264桌面流(WebRTC) / 终端 / 文件 / 数据库
```

---

## Phase 0 — 前置情报(不动目标, 30min)

**目标**: 资产清单 + 源站真实 IP + 技术栈确认

| 动作 | 命令/工具 | 产出 |
|------|----------|------|
| 子域枚举 | `dnsx -l subs.txt -resp` / crt.sh / Certspotter / HackerTarget | 全部子域 |
| 源站 IP | Censys 搜 `services.tls.certificates.leaf.names:"域名"`; Shodan `ssl.cert.subject.cn:"域名"`; SecurityTrails 历史 DNS | 绕过 CDN 真实 IP |
| 历史 DNS | ViewDNS.info / DNSdumpster / 病毒总 API | 换 CF 前的 IP |
| 邮件头溯源 | 给目标发邮件看 Received(SPF/DKIM 暴露 mail 服务器 IP) | 邮件服务器 IP |
| GitHub 泄露 | `github.com/search?q="域名"+password` / gitleaks | 密钥/配置 |
| 证书异常 | 证书 SAN 字段列出全部域名, 含内部域名(如 *.c2.internal) | 内部命名 |

**CF 前置关键测试**:
```bash
# 直连源站 IP 测 8080 是否绕过 CF 限制
curl --resolve 目标域名:8080:源IP http://目标域名:8080/
```

**空间测绘引擎语法**(额度精用):
- Censys(登录态 CDP 9227): 内容搜索找源站关键词, 每日 5-10 次搜索额度
- Shodan: `shodan.io/host/<IP>` 免登录看历史端口/banner; 搜索需登录
- Fofa(免费 100次/天): 中文特征强, 优先

**TGSEC 提醒**: 别只当记录员——每个发现问「能帮我走到哪一步?」子域→IP→端口→服务→漏洞链。

---

## Phase 1 — 黑洞突破(端口敲门逆向, 30min)

**目标**: 绕过 nftables 全局 DROP, 找到真实开放端口

### 1. 端口敲门(knock)逆向 ⭐⭐⭐
- 架构图明确 **2 步 API 握手** 触发敲门
- 敲门路径常藏在:
  - 前端 JS(`app.js`/bundle 里 `knock`/`handshake`/`port_knock` 函数)
  - **CF Worker / CF Page**(`worker.js` 可能实现敲门转发)
  - GitHub 泄露的配置(`knockd.conf` 是经典 Linux 敲门工具)
- **复现敲门**: 抓到序列后重放:
  ```bash
  knock -v <IP> 7000 8000 9000   # 经典 knockd 序列
  ```
- **关键**: 敲门是 UDP 还是 TCP? 抓前端 JS 确认协议, 构造同样序列

### 2. 探针端口分析(:8888)
- 心跳/beacon 端口(服务器主动外连 → 找 beacon 回调域名)
- 或「服务器探测客户端是否存活」→ 从 C2 控制台抓 WebRTC/websocket 流量找它

### 3. :8080「仅允许 CF」绕过
```bash
# 换 Host 头
curl -H "Host: 真实域名" http://源IP:8080/
# 换 HTTPS SNI
openssl s_client -connect 源IP:8080 -servername 域名
# X-Forwarded-For 伪造(部分系统只查 XFF 头!)
curl -H "X-Forwarded-For: 1.1.1.1" http://源IP:8080/
```

### 4. 全端口精扫(防 DROP/TUN 假象)
```bash
# ⚠️ TUN/代理会显示假 OPEN! 用 Python socket 精确探测 + HTTP 状态码判真伪
python3 - <<'EOF'
import socket
for p in range(1, 65536):
    s = socket.socket(); s.settimeout(0.3)
    if s.connect_ex(("TARGET", p)) == 0:
        print(f"OPEN: {p}")
    s.close()
EOF
# 重点端口: 22, 1234(SSH), 8080, 8888, 8889(PTY), 80, 443, 8000, 3000, 9000, 9090, 8443
```
- **HTTP 探测穿透 TUN 假象**: 裸 TCP 全通=假象, HTTP 503/404/200=真实;curl 走系统代理会掩盖直连, 用 urllib/--noproxy
- **被遗忘服务 = 最弱面**: Shodan host 详情页常发现全端口扫描漏掉的非业务端口(实战: 6666 Flask 开发服务器/20182 SSH/3000 Maintenance API)

---

## Phase 2 — 鉴权突破(HMAC 签名 + 令牌, 30min)

**目标**: 拿到合法令牌或绕过 HMAC 校验

### 1. HMAC 签名逆向 ⭐⭐⭐(最高价值)
- 架构: `时间请求 -> HMAC 签名令牌`
- **找密钥来源**(优先级):
  1. 前端 JS bundle 硬编码 key(`const KEY = "..."`) — **一步全链突破**
  2. GitHub/配置泄露
  3. **时间戳重放**: 若服务端只校验「时间戳新鲜度」(60s 内)不校验 nonce → 直接重放抓到的合法令牌
  4. 弱密钥爆破(短随机串 8 字符 → hashcat; **爆破不超 10min, 先找 JS 泄露**)
- **构造令牌**:
  ```python
  import hmac, hashlib, time
  ts = str(int(time.time()))
  msg = f"{ts}|{method}|{path}".encode()
  sig = hmac.new(b"LEAKED_KEY", msg, hashlib.sha256).hexdigest()
  print(f"X-Auth: {ts}.{sig}")
  ```

### 2. 敲门后的会话维持
- 敲门 2 步握手成功后服务端下发**临时 token/session**
- 抓握手响应(CDP 浏览器或 mitmproxy)→ 提取 token 结构 → 看能否伪造/重放

### 3. API key 自助申请(审计报告 F-02 思路)
- 检查是否有免审核的 key 申请接口: `/api/v1/keys/apply`、`/user/api-key/apply`、bot 内「申请 key」按钮

### 4. 对照「默认弱口令先行」铁律
- **先试默认弱口令再谈漏洞**(实战血泪: 死磕 14 类高端漏洞, 入口却是 admin/admin)
- 枚举常见默认口令: admin/admin、admin/123456、密码=账号名、test/test
- 验证码不是障碍: ddddocr 秒破 4 位数字验证码(captcha 返回 key+img base64 → OCR → 登录)

---

## Phase 3 — 控制面突破(Vue Console + API, 30min)

**目标**: 打进 Vue C2 Console / PTY 8889 API

### 1. 前端 JS 全量逆向(Vue Console) ⭐⭐⭐
```bash
# 下载 bundle
curl https://目标/assets/index-*.js
# 提取 API 端点 / WebSocket / WebRTC / 硬编码凭据
grep -oE '"/[a-zA-Z0-9_/-]+"' bundle.js | sort -u
# chunk 列表(懒加载): 从主 bundle 的 import("./xxx.js") 提取, 批量下载
```
- **提取清单**:
  - 所有 API 端点(`/api/...`、`/console/...`、`/pty/...`)
  - **WebSocket 地址**(wss:// 控制台实时终端)
  - **WebRTC 配置**(H.264 桌面流 → STUN/TURN 服务器, 可能泄露内网)
  - **硬编码凭据/密钥**(搜 `password`/`secret`/`token`/`api_key`)
  - 客户端注释里的隐藏域名(实战: 注释掉的 backaddress → nslookup → 全新后台 IP)

### 2. API 未授权测试
| 测试 | 手法 | 预期 |
|------|------|------|
| IDOR | 遍历 `/console/session/{id}` `/users/{id}` | 越权看他人会话 |
| 参数注入 | `qty=0/-1/abc` | 服务端宽容 → 异常行为 |
| 路径穿越 | `filename="../../../etc/passwd"` 上传/下载 | 文件读 |
| SSRF | 控制台「文件/数据库」功能传 URL | 内网探测 |
| JWT 篡改 | alg=none / 弱密钥 | 伪造 admin |

### 3. WebSocket/PTY 终端
- `wss://目标/pty/ws?token=...` — token 可重放/伪造 → **直接拿终端**
- WebSocket 不校验 Origin(常见)→ 跨站连接

### 4. 数据库功能
- 控制台有「数据库」入口 → 找 `/api/db/query`、`/api/db/export`
- 未授权 SQL 查询接口 = **直接拿数据**

### 5. 上传接口探测方法论(抢 shell 面)
- 参数名从错误消息确认(`Required request part 'file[]'` → 字段名 = `file[]`)
- 扩展名黑名单行为: 单 jsp/jspx/war → 400; `.txt.jsp` 双扩展 → 500(通过黑名单校验!) = 可能落盘
- 存储路径探测: `/api/upload/<filename>` 200 空 = Spring 接管; nginx SPA 回退全 200 HTML, **必须区分 HTML vs 文件内容**
- 后端功能坏(500)立即换面, 别死磕

---

## Phase 4 — SSH 突破(1234 端口, 敲门后)

**目标**: SSH 弱口令/密钥

- 敲门成功后 :1234 开放 → 尝试:
  - 弱口令(root/toor、admin/admin123、test/test)
  - **泄露的私钥**(GitHub/配置里的 id_rsa)
  - 审计报告「爆破穷尽表」思路: 7 算法离线爆破
- 注意频率(间隔 2-3 秒低调)
- 用户枚举被防时(Permission denied 统一)→ 别浪费时间枚举

---

## Phase 5 — 后渗透(内存沙箱 + 资产)

**目标**: 从控制台到服务器控制权

### 1. 内存沙箱逃逸
- 「内存沙箱(无痕执行)」可能基于 gvisor/firecracker/容器
- 已知逃逸链: docker escape / runC CVE / gvisor escape
- **更实际**: 找沙箱执行命令 API(`/api/sandbox/exec`)→ 参数注入 → 逃逸

### 2. 控制台资产提取(对照审计报告 F-03)
- 检查批量导出接口: `/api/assets/export?format=zip`
- 批量无限制 = 大量提取

### 3. WebRTC 桌面流
- H.264 桌面流 = 操作员真实桌面画面 → 抓流看操作 → 偷凭证(键盘记录式)
- SDP 交换里 candidate 可能泄露内网 IP

### 4. 持久化(拿到控制权后)
- **改 admin 密码**(无新增账号, 列表正常, 管理员自己都进不来)
- **新增隐藏管理员**(列表多一个账号=显眼, 仅当管理员不常看时用)
- 创建后门账号要点: 默认昵称+空头像(跟其他账号一致, 别画蛇添足)
- JWT 无状态缺陷: 改密码不会让已签发 token 失效 → 先签长期 token 再改回密码 = 双保险

---

## 攻击链总图(可落地顺序)

```
[Phase 0] 子域枚举 + 源站IP(绕CF) + GitHub泄露 + 证书SAN
    ↓
[Phase 1] 前端JS逆向 → 找敲门序列/硬编码key → 端口敲门 → 黑洞突破
    ↓
[Phase 2] HMAC密钥 → 构造合法令牌 → 或重放旧令牌 / 默认弱口令
    ↓
[Phase 3] Vue Console API枚举 → 未授权接口 → WebSocket终端 / 数据库 / 上传
    ↓
[Phase 4] SSH 1234 弱口令/密钥(敲门后)
    ↓
[Phase 5] 内存沙箱逃逸 → 服务器控制权 → 全部资产提取 → 持久化
```

**优先级排序**:
1. ⭐⭐⭐ 前端 JS 硬编码密钥(一步拿 HMAC → 全链突破)
2. ⭐⭐⭐ 敲门序列逆向(JS/CF Worker/GitHub)
3. ⭐⭐ CF 绕过源站直连(8080 查 XFF/Host 就伪造)
4. ⭐⭐ WebSocket 终端未授权(跨站连接/重放)
5. ⭐ 默认弱口令(admin/admin, 别死在高端漏洞上)
6. ⭐ SSH 弱口令(敲门后) / WebRTC 抓流(操作员画面=最终情报)

---

## 方法论铁律(跨技能融合)

1. **先默认弱口令, 再谈漏洞**: 打进去的钥匙往往是配置错误, 不是 0day
2. **基础层优先**: 高端 CVE 不通 → 回退全端口 HTTP/默认口令/DNS/子域/邮件服务器
3. **TGSEC 思维链**: 每个发现问「能帮我走到哪一步?」; 先动起来(看到 Swagger 翻 API, JWT 解码, .git 拖源码)
4. **别在同一个坑转圈**: 一个点堵 2 小时换面; 目标可能有 5 个入口
5. **诚实边界**: 打不通换面, 不硬刚 WAF; 每阶段记录失败原因, 换路径
6. **「打进去」标准 = shell/控制权**: 扒数据/API key 不算成功, 要明确告知用户

---

## 对照审计报告教训(必须避免)

| 报告教训 | 本目标对应 |
|---------|-----------|
| F-01 彩虹易 return_url 弱校验 → 免付充值 | 检查支付/充值接口 notify/return 是否可回放 |
| F-02 API key 免审核 → 全站可见 | 检查 key 申请接口 |
| F-03 批量无限制 → 大量提取 | 控制台批量导出接口 |
| 爆破穷尽表(7 算法全失败) | 不要死磕 HMAC 爆破, 先找 JS 泄露 |
| 未攻破项诚实声明 | 每阶段记录失败原因, 换路径 |

---

## 时间盒与资源分配

- **Phase 0-1(情报+黑洞)**: 30 分钟
- **Phase 2(HMAC 突破)**: 30 分钟(JS 逆向优先, 爆破不超 10 分钟)
- **Phase 3(控制台)**: 30 分钟
- **Phase 4-5(SSH+沙箱)**: 30 分钟(依赖前序成功)
- 总计 ~2 小时一轮; 失败 → 换目标/换思路, 不无限深挖

---

## 最终交付标准

- **DMZ 达成**: 拿到控制台/终端/数据库之一 = 成功
- **证明**: 控制台截图 / 终端命令输出 / 数据库导出
- **报告**: 资产拓扑 + 攻击链 + 复现步骤 + 证据 + 修复建议(正式报告格式: 执行摘要/漏洞详情含复现命令/利用链/盈利性分析/修复建议/证据附录, 存 D:\渗透\<目标>_recon\ + 桌面)

---

## 关联技能(融合调用)

- `cloudflare-bypass` — Phase 0 源站 IP 寻找的完整打法(Censys 内容搜索/--resolve 验证/直连)
- `server-getshell-playbook` — Phase 3 上传 getshell 完整路径 + 默认弱口令铁律 + 隐藏后台发现链
- `space-mapping-engine-recon` — Phase 0 空间测绘引擎语法与额度
- `bot-panel-spacemapping` — 找管理面板/登录态恢复
- `network-pentest` — 端口扫描/服务枚举
- `post-exploit` / `persistence` — Phase 5 后渗透与持久化
