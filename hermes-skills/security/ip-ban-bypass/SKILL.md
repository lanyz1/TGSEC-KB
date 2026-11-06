---
name: ip-ban-bypass
description: "Use when IP风控/拉黑/换出口/解封。诊断→跳板探测→paramiko SOCKS5隧道换出口。"
---

# IP Ban Bypass — 目标侧 IP 风控绕过(换出口作战包)

**定位**:目标(API/Web/商户网关)对来源 IP 拉黑/风控时的系统化绕过。适用:商户 API 网关、发卡/博彩后台、任何"换出口就能继续打"的场景。2026-09 OKPay 实战验证全流程(案例: references/okpay-2026-09-bypass.md)。

## 1. 诊断(先确认是 IP 层风控,别瞎换出口)

- **IP 层风控特征**:正确 token / 错误 token / 无 sign / 不存在 ID **全部返回同一错误**(如「身份认证失败」)——请求根本没走到验签
- 能区分"成功 vs 凭据错误" = 不是 IP 问题,别换出口浪费时间
- 排除干扰:目标可能同时有"商户级 IP 白名单"配置(文档常写)——换 IP 后仍全失败时查这条;拉黑的特征是**换干净出口立即恢复**

## 2. 出口来源与纪律

- 可用出口:用户提供的跳板池(多台并行探测)、v2rayN 节点切换(⚠️ 动全局代理,先问用户)、既有隧道
- **绝不污染专用资产**:95306 采集机 / COD 业务站隧道 / 数据管道服务器不用于渗透(项目隔离铁律,用户多次强调)
- 多台并行探测:paramiko 连每台 exec `curl -s -m 10 -o /dev/null -w '%{http_code}' -X POST https://<目标>/<api路径>` 看可达性;4 台里 3 通 1 认证失败 = 正常,直接弃失败那台
- ⚠️ **出口验证用目标 API 本身,不是 ipify**——国内电信跳板访问 api.ipify.org 常超时/被墙,ipify OUT 空 ≠ 隧道坏,勿误判

## 3. paramiko SOCKS5 隧道(免 sshpass/免 pty,后台稳跑)

`ssh -D` 要密码交互,后台无 tty 会卡;sshpass 常未装。**paramiko 编程式认证 + 自实现 SOCKS5 转发**解决:

```bash
python scripts/jump_socks.py <jump_ip> <jump_port> <user> <pass> <local_port>
# 例: python jump_socks.py 103.109.21.198 22 root PASS 20800
# 本地 SOCKS5 = 127.0.0.1:20800, requests 用 {"http":"socks5h://127.0.0.1:20800","https":"socks5h://127.0.0.1:20800"}
```

实现要点(见脚本):SOCKS5 no-auth 握手 → 支持域名 CONNECT(ATYP=3)→ paramiko `open_channel("direct-tcpip", (host,port), ...)` → select 双向 relay。长驻进程用 terminal background=true 静默跑。

## 4. 解封判定与新出口纪律

- 换新出口后:**正确凭据 → success / 错误凭据或不存在 ID → 失败(两者可区分)** = 新出口干净,旧 IP 拉黑确认
- 解封探测可后台挂轮询脚本(每 5 分钟一次,解封写 flag 文件通知),不占主线
- **新 IP 纪律(防二次拉黑)**:低频少量请求、间隔 1-2s、不复用触发拉黑的恶意 payload(SSRF/metadata 域名探测是「记录取证」拉黑直接诱因,一次触发=整段 IP 拉黑);一次只改一个变量

## 4e. WAF Content-Type 绕行（★ 云 WAF 通杀）

多数云 WAF（阿里云 WAF 实证）只检测 `POST + application/json` 族的请求体。**换 Content-Type 即完全绕过**：

```python
# 原始（被 WAF 检测）
headers['Content-Type'] = 'application/json'

# 绕过变体（请求体原样到达 App 层，WAF 不检测）
bypass_types = [
    'text/json',
    'application/x-json',
    'application/json-patch+json',
    'application/jsonrequest',
    'text/plain',                 # 部分后端也接受
]
```

**条件**：后端框架需能解析非标准 Content-Type 的 JSON 体（Spring Boot / Express 通常可以）。

## 4f. WAF XFF 记账绕过（★ IP 永不封禁）

云 WAF 的 Rate Limit / IP Ban 按 `X-Forwarded-For` 计数而非 TCP 源 IP：

```python
import random
def random_xff():
    return f"{random.randint(1,254)}.{random.randint(0,254)}.{random.randint(0,254)}.{random.randint(1,254)}"

# 每请求伪造唯一 XFF → 真实出口 IP 封禁计数恒为 0
headers['X-Forwarded-For'] = random_xff()
```

**效果**：WAF 永远不触发 IP 封禁（实测阿里云 WAF）。
**不适用**：Cloudflare 等不信任客户端 XFF、用 CF-Connecting-IP 的 WAF。
**来源**：极融 ARES 案（`极融ARES报告知识蒸馏_20260922.md`）

## Pitfalls

- urllib + socks 打 HTTPS 报 SSL EOF → 用 requests + socks5h 代理
- 触发「已记录取证」/「请求包含非法内容」类响应 = 拉黑信号,立即停手评估
- IDOR/越权测试前先理解目标验签模型:HMAC 签名含 id 且服务端按 id 找 token 验签 → 跨商户天然失败,别浪费请求;真正值得测的是"同 token 不同资源"与响应签名一致性
- 响应验签 FAIL(服务端对数组型响应的签名方式与请求不同)可能是平台实现 bug——记录,别当自己 SDK 坏了无限排查

## 关联

- `proxy-chaining`:匿名链/多跳(不同目标:攻击者侧匿名 vs 本技能:目标侧拉黑)
- `v2rayn-proxy-ops`:v2rayN 节点运维(换节点动全局,先问用户)
- `tg-bot-live-pentest`:商户 API 网关场景(本技能是它的「换出口」升级件)
- `cyber-ops`:作战指挥层(本技能作为战术件被引用)
