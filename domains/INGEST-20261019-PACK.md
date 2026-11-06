# INGEST-20261019-PACK — 战报包吸收（11 份报告）

> 来源：`报告.zip`（3.85 MB / 21 文件 = 8 份主报告 + 10 个嵌套证据包 + 1 PDF + 1 tar.gz，2026-10-19 落地）
> 性质：真实战役报告合集（客服后台 / 发卡 / 订阅转换 / AI 建站 / 博彩点控 / 白标体育 / 验证码）
> 纪律：原文留本机案卷（`/root/intel/reports_20261019/`），**原文不入库**；明文凭据、源站 IP、客户 PII 一律不落库。

## 一、战报 → case-lessons（本仓）

新增 **12 课**：

| 域 | slug | 一句话 |
|----|------|--------|
| auth-security | `sonata-code-array-totp-secret` | `_code[]=1` 打崩 `hash_equals`，debug 帧参数吐 TOTP secret |
| auth-security | `zgycpd-lockout-oracle-budget` | 15min 锁窗 + 三级错误文案预言机，2-shot/16min 预算 |
| auth-security | `botion-point-captcha-mask` | 遮罩吃鼠标事件；序号 1/2/3 才是成功；22411=密码对 |
| api-security | `lynxcode-heapdump-whitelist-takeover` | heapdump 白名单三连：发 token / 自封超管 / 读源码 |
| api-security | `dalikefu-backup-2fa-skip` | 目录 403 但备份直读；登录 code 空值绕过 2FA |
| web-attack | `subconverter-getlocal-quickjs-rce` | `/getlocal` 任意读 + `filter_script` QuickJS RCE + Cloudreve 写 root |
| web-attack | `playtube-social-login-forge` | `social_login` 伪造 base64 token → `user_id=1` 管理员 |
| web-attack | `phpstudy-workerman-root` | UEditor catchimage/phar → phpstudy 9080 → Workerman root |
| gambling-pentest | `ttzslots-gameinternal-rtp-control` | 去 `/admin` 前缀的未授权点控：RTP / 养客 / 杀客字段全表 |
| gambling-pentest | `v66-seo-poison-front-token` | SEO 壳 → 导航 config 未鉴权 → CMS XSS 偷前台 token |
| recon | `ydt-ops-origin-topology` | 云顶盾 Ops 弱口令 → rules 表即回源拓扑 |
| business-logic | `we7-cashier-fee-tamper` | 微擎收银台金额/fee 客户端可控；只定性到展示层 |

CASE-INDEX：课数 **127 → 139**；域计数同步（api 18→20 / auth 6→9 / business 20→21 / gambling 14→16 / recon 13→14 / web-attack 20→23）。

## 二、本机技能库同步（不入仓）

| 动作 | 数量 | 落点 |
|------|------|------|
| 新建胖卡 | 3 | `sonata-admin-pentest` / `subconverter-pentest` / `playtube-pentest` |
| 旧卡增量 | 9 | 2FA 数组注入 / heapdump 白名单 / Cloudreve 策略写 / gameInternal 点控 / phpstudy+Workerman / botion 实测 / 锁窗预算 / Ops 面板 / 微擎金额 |
| 纠错 | 1 | 锁窗口径由「2 次错密」改为「15min 窗口 + 实测 2-shot；阈值因后台而异」 |

## 三、未吸收 / 边界

- 报告内明文口令、TOTP 种子、bot_token、源站 IP、客户邮箱与手机号：**全部不落库**。
- `AUDIT` / `SKILL-AUDIT` 为内部自检，非攻击面，不入 case。
- aixiaoka 金额篡改只到收银台展示层，未走到建单/回调核额 → 只写「金额可被指定」，不写资损。
- 报告里的「目录 403」不等于不可读；反例已写入 dalikefu 课。

---
@TGSEC社区 · @TGSEC-Qtzuu 整理 · 2026-10-19
