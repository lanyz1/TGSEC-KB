# INGEST-20261022-PACK — 报告包 + 同行作业机（两批）

> 日期：2026-10-22 · 批次：`pack-20261022`（A 批）+ `peer-loot`（B 批）
> 原则：原文与凭据不入库；只落可复用手法（case-lessons）与本机技能卡。

## 1. 来源与体量

**A 批 — 报告.zip**

- 包体 **608,296,870 字节**（约 580MB），解包 **7,962 个文件**
- 构成：156 份报告 md · wefe.cc 交付 32 份 · 外部技能库 911 张 · PEER_LOOT 480MB
- 落点：`/root/absorb_pkg/`（本机案卷，未入库）

**B 批 — 同行作业机（PEER_LOOT 566 文件）**

- 4 篇分析 md（约 260KB）：Coruna 全链拆解、逐 CVE 分析、AI 渗透方法论与提示词库
- `.bash_history` 150KB：真实操作序列（工具链、跳板、反取证习惯）
- 其余为二进制/明文台账/扫描结果，按纪律只登记不入库

## 2. 战报 → case-lessons

**A 批（已随 5a8f35eb / 9235ab69 入仓）**

| slug | 一句话 | 域 |
|------|--------|----|
| `tgbet6684-ruoyi-druid-fleet` | 78 机 RuoYi 白标集群：`.html` 后缀白名单绕过 + Druid 三步登录通杀 18 节点 | gambling-pentest |
| `dujiaoka-epusdt-channel-mismatch` | 独角数卡通道错配泄露 merchant_pem/sign → 伪造 notify 回调 0 元购 | business-logic |
| `tg-account-panel-mass-export` | TG 筛号平台：注册附 role=admin + batch-export 回 .session 即接管 | api-security |
| `goflylivechat-jwt-hardcoded` | 开源客服系统硬编码 JWT secret + 空 RbacAuth → 在线监听/顶号 | gambling-pentest |
| `wefe-tiktokmall-zeroauth-full-dump` | `.action!method` 三层零凭据拖库 + `type=1` 破脱敏 | api-security |

同批入库：`docs/playbooks/` **87 页**（含 INDEX）· `tools/ops/` **157 个**作业脚本。

**B 批（本批新增 5 课）**

| slug | 一句话 | 域 |
|------|--------|----|
| `blind-sqli-byte-length-oracle` | 盲注用响应字节数做布尔判据（真 10,687B / 假 7,473B），阈值取中间 | web-injection |
| `php-webshell-stealth-trio` | `/dev/shm` 落点 + `postpass` 盐 Cookie + `X-Accel-Buffering:no` | web-attack |
| `nginxwebui-default-admin` | NginxWebUI 8000：无鉴权 version 指纹 + `admin/admin` → 证书私钥 / 配置重载 | web-security |
| `ncat-proxy-single-hop-ssh` | `ncat --proxy` 塞 ProxyCommand 单跳 SSH，替代 proxychains 全局劫持 | redteam-framework |
| `coruna-ios-stage-matrix` | 水坑 iOS 版本→Stage 载荷映射写在前端 JS，可离线还原 | reverse-engineering |

**旧账补索引（5 课，早已在仓但未进 CASE-INDEX）**

`double-content-type-parser-disparity` · `graphql-sort-to-es-painless` · `zhangduozhe-api-router-and-weakadmin` · `appinsights-js-connection-string` · `fcgi-socket-sendmail-disable-bypass`

CASE-INDEX：**142 → 147 课**（域计数按实际文件重算，去掉此前的手工漂移）。

## 3. 本机技能库同步（不入仓）

- **新卡 3 张**：`tg-bot-ops` · `heapdump-lanniao-hunter` · `bb-local-toolkit`
- **升级 1 张**：`1z-gambling-family-pentest`（白标 1Z 家族签名/验证码/后台面）
- **B 批增量 6 张**：`sqli-manual`（字节数判据）· `webshell-stealth-persistence`（PHP 大马三件套 + 落地即删日志）· `self-hosted-panel-takeover`（NginxWebUI）· `network-tunneling`（`ncat --proxy`）· `darksword-coruna-c2-pentest`（版本→Stage 表）· `llm-security`（九框架提示词库 183KB 落 references）
- 另有 27 张卡 / 35 处 TTP 增量（Druid 三步登录、`.html` 白名单、422 判鉴权、卡商密钥面等）

## 4. 未吸收与边界

- **不入库**：`13_cloud_aksk`（11,101 行云凭据）、`12_recon_189cn`（44MB masscan）、`01_php_webshell`（免杀马构建器）、`02_ios_exploit_kit`（22 个可运行 exploit）、115 个硬编码目标的一次性脚本
- **未吸收**：908 张同名技能（内容不比库内新）· R64 844KB 卡密台账 · PEER_LOOT 二进制与明文凭据
- **未验证**：报告里的金额/条数口径按原文照抄，未二次核验；涉及“可造成资损”的结论只写到“可被指定/可达”
- **脱敏**：明文口令、TOTP 种子、bot_token、源站 IP、客户 PII 一律零落库；本文出现的 `admin/admin` 为产品默认口令，非目标实号

@TGSEC社区 · @TGSEC-Qtzuu 整理
