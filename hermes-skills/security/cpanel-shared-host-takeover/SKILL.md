---
name: cpanel-shared-host-takeover
description: "Use when a cPanel/WHM shared host: upload RCE → account radius → .env/DB → hidden SSH."
---

# cPanel 共享主机接管链（单洞大半径）

**适用**: cPanel/WHM 共享虚拟主机——单账号洞 → 同机多站/多库半径。
来源: 2026-10 skyline/hunterjungle 案（28 站 / 27 库）。

## 指纹

- 端口: 2082/2083（cPanel）· 2086/2087（WHM）· 2095/2096（Webmail）· 21（Pure-FTPd）· 5666（NRPE）
- **SSH 可能不在 22**（案中在 21098）——top2000 会漏；从内部 `ss` 发现
- 同 IP 顶级域 = 共享主机判定；`uid=10xx` 类虚拟账户

## 链（八步）

1. httpx 多站指纹 → 找**上传/解析组合**（案中: FoxQR `QrController.php` logo 零校验 + `/uploads/` 目录列举 + PHP 解析）
2. `/uploads/` 列举先查**历史 webshell**（长期可打点信号）
3. 上传注意 **「响应 500 但文件先落盘」** 判据（以文件系统事实为准，勿被状态码骗）
4. RCE → 读同账号全部站源码 → `.env`/配置（明文 DB 凭据 + APP_KEY + 管理员口令）
5. `127.0.0.1:3306` 本账号**全库枚举**（SHOW DATABASES 实测）
6. 明文管理员口令**实测登录**业务系统（302→/home 判据）
7. 持久化: 冰蝎马（AES-128-CBC）同点投递
8. SSH 发现 → 写公钥 → `ssh -N -D` SOCKS（**jailshell 只禁交互 shell，端口转发不受影响**）→ 打外网不可见服务（WHM 2086 / cPanel 2077/2079 / Go 高端口 / Memcached）

## 纪律与事故预防

- `.user.ini` 缓存（5 分钟）→ 语法错误整站 500: `php -l` 先验 + base64 传源码再启用
- 清理: 我方文件全删 + **他人 webshell 原样保留**（勿代清理）+ 业务可用性回归
- 「端口分布过于一致」= 透明代理层，勿计存活

## When to reuse

- 案例: `domains/web-attack/case-lessons/skyline-cpanel-28site-chain.md` · `cyberpanel-source-ssh-chain.md`
