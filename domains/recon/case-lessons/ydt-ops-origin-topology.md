# 案例课：盾/加速器 Ops 弱口令 = 回源拓扑倍增器（YDT 云顶盾）

> 来源：报告包 jxpmm（2026-10）· 域：recon

## 一句话

`/ops/session` 用 `admin/admin123` 进去后，`rules` 表就是一张**域名 → 源站 IP:端口**的回源清单；CDN/WAF 后面的宝塔、FTP、MySQL、MinIO、彩票后台一次全现形。

## 指纹

- `/ops/session`（不是 `/ops/login`，后者常 405）
- `/ops/apps/<appid>/rules`、`/ops/apps/<appid>/private-nodes`
- 面板标题含「云顶盾 / Ops」

## 链

1. `POST /ops/session` 弱口令 → 会话
2. 拉 `rules`：每行规则名 → `<origin-ip>:<port>`（bt20531 / ftp21 / mysql3306 / minio9000 / lot8090）
3. 拉 `private-nodes`：节点网关（`:19443`）
4. 拉 `credential`：SDK `pid`/`key`、启动串
5. DoH 短记录 `_ydt-short-<pid>.<domain>` TXT → 可解节点 IP

## 用法

- 拿到源站后 **SNI/Host + 证书** 实证再打，别盲扫 IP
- 优先宝塔 20531、MySQL 3306、MinIO 9000/9001
- 同族 Ops 常同口令：换域名/IP 再试一次
- 宝塔假 404：先取基线与 `len`/`md5`，再跑 4 位 hex；hits=0 说明入口不在该空间

## 边界

- rules 是「当前生效」配置，不等于所有端口对公网开放
- 节点 IP 可能只是中转，不是业务源站
- 弱口令只测默认，别把兄弟面板打成字典喷洒

## 检查清单

- [ ] `/ops/session` 指纹
- [ ] 默认口令
- [ ] rules/private-nodes/credential
- [ ] 源站 SNI+证书实证
- [ ] 宝塔/MySQL/MinIO 优先级

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
