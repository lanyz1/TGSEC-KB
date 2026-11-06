---
name: lanzou-pan-recon
description: "Use when 解析蓝奏云(lanzou)分享做分发挖掘. 列目录+直链协议+acw_sc__v2."
---

# 蓝奏云分享解析与分发挖掘

## 触发
- loader 配置 / 落地页 / 文档里出现 `*.lanzou*.com` `*.lanzoux.com` `*.lanrar.com` 分享链（如 `wwyu.lanzoue.com/b00mp10sve`、`xiaodao.lanzoub.com/i62M535ok4if`）。
- 要摸清某运营方经蓝奏分发的产物清单，或要下载其分发的大文件（客户端/资源包）。

## 0. 铁律
1. **两段式**：`/b` 开头（如 `b00mp10sve`）= 文件夹页（可列目录）；`/i` 开头（如 `iGiaj4at33di`）= 文件页（先过 JS 挑战才有下载参数）。`duan` 字段 = 文件短 id，页面 id 与短 id 均可访问文件页。
2. **HTTP 200 不代表成功**：蓝奏对可疑请求回**挑战页也是 200**。判真页看 `<title>... - 蓝奏云`，不看状态码。
3. **gzip 纪律**：响应可能 gzip（即使没请求要）。请求带 `Accept-Encoding: identity` 最稳；若仍收到 gzip 包，**先 `gzip.decompress(b)` 再 decode** —— 千万别把原始响应 decode(errors='ignore') 存成文本，字节会被毁掉（踩过：保存的挑战页再也解不开）。
4. 全程固定同一 UA + 一个 cookiejar（挑战 cookie 绑 (IP, UA)）；直链一次性，拿到立即下载。

## 1. 文件夹列目录（filemoreajax.php）
1. GET 文件夹页 `https://<host>/b00mp10sve`（host 前缀 wwyu/wwyv/... 随机分配，从原链原样用）。
2. 页内抓五个参数：`fid`、`uid`、`puid`（90+ 字符长串）、`k`、`t`。
   - **`k`/`t` 的变量名每次加载随机**（如 `ibf0oh='1791120451'`、`_hdcqa='72cb…'`）——必须从当次页面抓：全页找 `'[0-9a-f]{32}'` 字面量 ⇒ k；找 `'\d{10}'` 字面量 ⇒ t。**绝不能写死变量名。**
3. POST `https://<host>/filemoreajax.php?file=<fid>`（Referer=文件夹页、`X-Requested-With: XMLHttpRequest`、UA），body：
   `lx=2&fid=<fid>&uid=<uid>&puid=<puid>&pg=1&rep=0&t=<t>&k=<k>&up=1&vip=0&webfoldersign=`
4. 返回 JSON：`{"zt":1,"info":"sucess","text":[{"name_all":"2.exe","size":"80.5 M","time":"18小时前","id":"iGiaj4at33di","icon":"exe"},…]}`。
   - `id` 拼 `https://<host>/<id>` 即文件页；`pg` 递增翻页；`size`/`time` = 免费拿到**发布清单 + 更新节奏**。

## 2. 文件直链（2025+ 现行协议；旧流程已死）
1. GET 文件页 `https://<host>/<fileid>`。若返回 2–5KB、含 `var arg1='…';(function(a,c){var G=a0j…})` = **acw_sc__v2 挑战（可离线解，非死面）**：
```python
BOX = [15,35,29,24,33,16,1,38,10,9,19,31,40,27,22,23,25,13,6,11,39,18,20,8,14,21,32,26,2,30,7,4,17,5,3,28,34,37,12,36]
KEY = '3000176000856006061501533003690027800375'
def acw_sc_v2(arg1):          # arg1 = 挑战页里的 40 位 hex
    q = [''] * len(BOX)
    for x, ch in enumerate(arg1):
        for z, mv in enumerate(BOX):
            if mv == x + 1: q[z] = ch
    u = ''.join(q)
    return ''.join(format(int(u[i:i+2],16) ^ int(KEY[i:i+2],16), '02x')
                   for i in range(0, min(len(u), len(KEY)), 2))
```
   流程：抓 `arg1='([0-9A-F]{40})'` → 算值 → 带 `Cookie: acw_sc__v2=<值>`（+原 cookiejar）**重 GET 同一 URL** → 真页。页内排列盒与公版 BOX 逐位相同 ⇒ KEY 即公版（多站实测）；不同再从混淆数组还原 `L(0x115)`。
2. 真页（~2KB，`<title>文件名 - 蓝奏云`）含 `<iframe src="/fn?...">` → GET `https://<host>/fn?...`（同 cookie、Referer=文件页）。
3. /fn 页 JS 抓下载参数：
   - `wp_sign`（长 base64 串）→ 提交时作 `sign`
   - `ajaxdata`（短串，如 `yLZl`）→ 同时作 `websignkey` 和 `signs`
   - `kdns`（默认 1）+ 固定 `ves=1`
   - 提交域取页内 `domain1 = https://apifile.woozooo.com/ajaxfile.php?file=<fid数字>`；回退 `domain2 = apifile.lanzouw.com/...`；kdns==0 的 KDNS 变体直链域 = `https://developer2oss.lanzouc.com:661`。
4. POST 上述 ajaxfile.php（Referer=/fn 页）：
   `action=downprocess&websignkey=<ajaxdata>&signs=<ajaxdata>&sign=<wp_sign>&websign=&kd=<kdns>&ves=1`
   → `{zt:1, dom:…, url:…}` → **直链 = `dom + '/file/' + url`**，立即下载。

## 3. 坑（省时间用）
- **旧流程是死路**：用页内 `wsk_sign`（形如 `c20230908`）+ 同域 `/ajaxm.php` POST → 恒回 `{"inf":"密码错误"}`。真 sign = `wp_sign`，真端点 = `apifile.woozooo.com/ajaxfile.php`。别在旧流程上耗时间。
- **下载 API 不在分享宿主域上**：往镜像 host 自身请求 `/ajax.php?...` 类路径会撞上其服务端 PHP 报错（fatal/空响应）——宿主域只承载页面与 `filemoreajax.php` 列目录；取直链恒走页内 `domain1`（`apifile.woozooo.com/ajaxfile.php?file=<数字 id>`）。
- 挑战页与真页都是 200；判据 = `<title>` 有无 + 长度（真页 ~2KB 带文件名）。
- 随机变量名每次刷新都不同：解析器写完先重抓同页自证（两次变量名不同但流程一致）。
- 蓝奏对境外/数据中心 IP 更常挂挑战；CN 住宅出口（本机直连）反而顺。

## 4. 武器化场景（分发挖掘）
- 运营方把**完整产品**（几十~几百 MB 的 exe/zip）放蓝奏分发：目录清单里 `2.exe`(80.5M)/`2.zip`(326.9M)/`3.exe`(75M) 这类 = 比 loader/落地页大得多的独立逆向目标（完整客户端内嵌 API/更新服务器/配置）。
- 顺序：先列目录拿「清单+时间线」，再挑**小体量 exe 先下**（解剖最快），zip 后补。
- 直链失败就重走第 2 节（重解挑战取新直链）。
