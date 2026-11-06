# 从精简库吸收独有卡（2026-10-22 实账）

背景：worker B 换上全量库后，旧精简库被 `mv` 到 `/root/skills.thin-<date>`（160 张），作为吸收原料保留。用户一句「上面有可吸收的吗」触发本流程。

## 漏斗

| 阶段 | 数 | 方法 |
|---|---|---|
| 旧库卡数 | 160 | `find -name SKILL.md` 取父目录名 |
| 本机没有的名字 | **59** | 目录名差集（本机当时 2171） |
| 与本机最近邻 Jaccard | 全部 ≤0.05 | 5-gram shingle，去 frontmatter，逐张比对 |
| 收 | **33** | 「新攻击面」才收 |
| 丢 | 26 | 同面已有平级卡 / 二选一 |

去重三连（都在 `/root/audit-20261022/`）：`triage60.py`（元数据 + `difflib` 最近邻）、`overlap60.py`（同族关键词找同类卡）、`dup60.py`（5-gram shingle Jaccard）。结论是 **Jaccard 全 0**，证明不是改名/改写副本，才进入「按面判」。

## 收的 33（按面）

`web-api-auth-surface-audit`（Druid `/druid/weburi.json` 只保留约 1000 行、JVM 重启即清空；各模块 `/<gateway>/<module>/v2/api-docs` 常驻白名单）· `selfhosted-panel-exploitation`（RuoYi/Druid + MinIO + New API + 宝塔 + Proxmox + fnOS + frps + x-ui 的整段扫描顺序；虚拟化 DC 里 ping 扫描全假、网关 ARP 代理整个 /24）· `card-issuing-platform-pentest`（先建模真实费率再测卡数据，别把陈旧 BIN 报错当「已加固」）· `jingfaka-platform-pentest`（鲸发卡 v9–v13 nulled 源码 `application/route.php` 就是端点表）· NFS+rpcbind · SockJS/STOMP · noVNC/websockify · TokenPay · 包网白牌接入 · Cocos 客户端 · 韩国 DART 财报 · 发卡站未售库存提取 · 面板配置→命令执行 · 备份/恢复导出外带 · 反射 XSS 打操作员浏览器 · 反封锁镜像集群测绘 · C2 家族基建映射 · 加壳 APK→C2 面板 · New API/One API 网关 等。

## 丢的 26（理由）

thinkphp 6 张（本机 6 张同类）· 验证码 OCR 10 张（已有 10 张）· 报告写作 8 张（已有 8 张）· dujiao 2 张（已有 2 张）· engagement 收尾（已有 teardown）· 代理出口（已有 egress-proxy + chinese-proxy）· `nfs-exploitation`（与 `nfs-rpc-exploitation` 二选一）· `websocket-stomp-channel`（与 `sockjs-stomp` 二选一）。

**丢不等于删**：源卡留在 `/root/absorb-<date>/remote60`，要翻案随时取。汇报时要点明这一点。

## 收后闭环实测

1. 安装：33 张 → `~/.hermes/skills/security`，安装前 grep `secret|private_key|pwd=<REDACTED> 命中 0。
2. 重建：`{"total": 2204, "enabled": 430, "disabled": 1774, "legacy": 1856}`；门禁 `GATE OK（full） 2204/2204 · 30/30 · 94/96 · 96/96 · MISS 0 · 标题 8/8 · 正文 7/8`。
3. 抽测 8 条口语查询（鲸发卡 / NFS 2049 / SockJS STOMP / TokenPay / noVNC / DART…）→ 7 条 TOP3 命中；未中的 `发卡站 未售卡密 提取` TOP1 是同族 `acg-faka-pentest`，新卡在前五。
4. 落仓：`web-attack 12 / recon 8 / gambling-pentest 5 / other 8`，commit `bd0bc76a` 已推；`git grep '154\.219\.'` 与主机名均为 0。
5. 舰队：`sync33.sh` 只传 33 张 tar，两台 worker 各自重建，数值与本机一致（2204 / 430 / MISS 0）。
6. 分享包：`hermes-skills-20261022-1953.tar.gz.gpg` **43,422,194 B**，sha256 `a9b7d6e2d5417654954212182529dc2d5766ff76cb5b006071c1aeb331657712`，解密实核 `cards=2204 / ip_hits=0 / secret_hits=0 / seed=1805`；旧 `1912` 包删除。

## 这轮踩的坑

- **脱敏纪律卡自己泄漏**：`verify_pkg2.sh` 报 `2 files own IP / 1 secret`，全在 `tgsec-repo-publishing/SKILL.md` 与 `references/pre-publish-redaction-and-ip-opsec.md`——真实主机名、真实网盘 `pwd` 被当例子写着。修完后必须**重打包并再解包 grep**，源树 sweep 通过不算数。
- **卡数涨了基线分数不许变**：2204 张仍须 `94/96 · 96/96 · MISS 0`；分数掉先查 `.disabled.json` seed 是否 1805 条。
- **worker 只传增量**：全量包 43MB × 每台再传一次既慢又占磁盘（worker 只剩 ~8G），33 张 tar 只有几百 KB。
