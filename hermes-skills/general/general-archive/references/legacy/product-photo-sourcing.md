<!-- archived from /root/.hermes/skills/productivity/product-photo-sourcing/SKILL.md on 2026-10-21 -->

---
name: product-photo-sourcing
description: Use when 要给实物找全网真实实拍图,或判断商品图是实拍还是AI图. 图库批量抓取+真伪判据+图册交付.
---

> 归档卡：原目录 `/root/.hermes/skills/productivity/product-photo-sourcing`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/productivity/product-photo-sourcing/…')`，不要相对 `references/legacy/` 解析。

# 实物实拍图获取与真伪判据

## 先定层(否则结论会误导)
同一件东西横跨三条供给线,交付必须分开列:
1. 原品/真品 — 哪里能合法买、有什么渠道门槛
2. 复刻/模型/摆件 — 国内可下单的那一层
3. 假货与 AI 图 — 单独一组当反例
国内电商高度集中在第 2、3 层;不说清楚等于没交付。

## 抓图
- 走 curl/urllib 直连 Bing 图库异步接口,一条 query ~35 条,中文 query 同样有效(直出 1688/京东/知乎图源):
  `https://www.bing.com/images/async?q=<urlencoded>&first=1&count=35&mmasync=1`
- 结果藏在 HTML 的 `m="{...json...}"` 属性里:`murl`=原图、`purl`=页面、`t`=标题。
- 中文线 + 英文线 + 品牌官网线一起铺,统一去重;**按专业卖家域名白名单先筛再下载** —— 聚合站图质量差,白名单能一刀砍掉噪音。
- 现成脚本 `scripts/bing_image_harvest.py`:抓取→下载→md5 去重→出图册,内置超时护栏。
- 纯抓图不必上浏览器;浏览器自动化留给需要登录/交互的站点。

## 下载护栏(必须)
- `socket.setdefaulttimeout(8)` + 每请求 timeout=8 + 循环内墙钟硬止损。无超时的 urllib 会卡在不可达主机上,把 300s 的执行单元跑爆、已下的文件变半成品。
- 下载完按 **md5 去重**:超时重跑/多 query 交叉必然留下重复图。
- 带 `Referer: https://www.bing.com/` 过一部分防盗链;拍卖行/垂直站仍会 403/404,属正常损耗,跳过即可。

## 真伪判据(必须自己看图)
- **AI 图硬判据:图上文字是乱码拉丁字母**(铭文/logo/包装盒)。高溢价卖点(金色/镶钻/水晶)的电商主图大量是 AI 出图。
- 实拍:阴影不均、背景杂物/展示架/展示牌、可读包装码、环境纹理。
- 逐图判断,不能因为一张实拍就认定整店真实;细节见 `references/real-vs-ai-photo.md`。

## 交付(用户偏好)
- 落桌面一个目录,文件名带分组前缀(①真品 ②复刻 ③国内可下单 ④假图对比 ⑤同类拓展)。
- 同时出两件:`scripts/bing_image_harvest.py` 生成的 `00_gallery.html`(用 `::preview{file=...}` 内嵌聊天)+ 手写的 `货源与实拍索引.txt`(可点击链接 + 渠道/门槛说明写进文件,不要只留在聊天)。
- 聊天里只内嵌 3–5 张最贴近的图(`MEDIA:<绝对路径>`),不要全铺。
- 用户只说「找一下」时不要中途发问:三条线抓齐、图册落盘,最后再问一句方向。
