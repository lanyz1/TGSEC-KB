---
name: large-file-intake
description: "Use when user sends a big-file link (gofile) to ingest."
version: 0.1.0
tags: [gofile, download, intake, telegram, zip]
---

# 大文件入站：从文件托管链接取回数据

用户丢来 `gofile.io/d/...`、pixeldrain、catbox 链接（常见于 Telegram 入站墙挡住的大包）。目标：不依赖浏览器渲染，走 API 拉全量、验 MD5、解包。

## 通道事实

- **Telegram 入站（bot 下载用户发的文件）硬上限 20MB**：超限报 `The document is too large or its size could not be verified. Maximum: 20 MB.`，适配器还会把正文替换成通知文本、caption 一并吞掉。这是**下载**上限，与发送上限（~50MB）是两条线。
- >20MB 的包：让用户发网盘链接，或 `split -b 19m` 分卷。

## gofile 取数协议（2026-10-17 实测，118MB 全流程）

1. **游客票**：`POST https://api.gofile.io/accounts`（UA=Chrome）→ `data.token`（32 字符）。后续全带 `Authorization: Bearer <token>`。
2. **签 wt**：`/contents` 要**请求头** `X-Website-Token`（**query 传参无效；query 传还会得到误导性的 `error-notPremium`**）。wt = `generateWT(account_token)`，算法烘在 `/js/wt.obf.js` —— Node `vm` 里伪造 `navigator.userAgent/language` 后直接调用，别硬编码旧值；时间桶约 4h、服务端约 6h 轮换，现取现签。再配 `X-BL: en-US`。
3. **清单**：`GET https://api.gofile.io/contents/{contentId}`（contentId = `/d/` 后面那段）。单文件分享时 `data` 顶层直接给 `name/size/md5/link`，**`children: 0` ≠ 空分享**（只有文件夹才看 children）。
4. **下载真文件**：`data.link` = `https://store*.gofile.io/download/web/<fileId>/<fileName>`，**必须带 `Authorization: Bearer <token>` 或 cookie `accountToken=<token>`**。裸 curl 会被 302 弹回 `gofile.io` SPA 壳（约 3,358B HTML，看起来像“分享被墙/文件没了”）；带票即满速直出。
5. **验**：落地 `md5sum` == `data.md5`，三方对齐才算完。

**私有分享排查**：`{"status":"ok","data":{"canAccess":false,"public":false}}` = 分享没开公开（不是 premium、不是墙），前端这套组合只有 `notPublic` 一个分支。修法在用户侧：gofile 里把内容 **Public 打开**，同一个 `/d/` 链接立即可拉（实测同 uuid 开关一次即复活）。

## 解包

中文 Windows 打的 zip 文件名是 GBK 且无 UTF-8 标志，Python `zipfile` 读出来乱码 → `name.encode('cp437').decode('gbk')`（失败退 gb18030），解包前滤 `..` 防 zip-slip。用 `scripts/unzip_gbk.py`。

## 备选托管

pixeldrain（`/u/<id>` → `https://pixeldrain.com/api/file/<id>?download`）、catbox（≤200MB 直链）、0x0.st（≤512MB），或分卷走 TG。

## 文件

- `references/gofile-api.md` — 前端模块地图、payload 样本、踩坑记录
- `scripts/gofile_fetch.mjs` — guest→wt→contents→下载 的可复用脚本
- `scripts/unzip_gbk.py` — GBK zip 解包

## Pitfalls

- API 路线不依赖 DOM，比浏览器渲染快且稳；浏览器只适合人肉确认页面状态。
- store 下载不带票 = SPA 壳（3,358B HTML）；判断看 body 是不是 HTML，而不是文件流。
- wt 签的是**账号 token**，不是 contentId（早期按 contentId 签会 401）。
- 直链里文件名写错会被弹回 SPA 壳，别拿它探文件是否存在。
