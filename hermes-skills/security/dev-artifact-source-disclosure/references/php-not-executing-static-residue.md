# 「PHP 不执行」型残留:全站 `.php` 当文本裸奔(能读源码,拿不到 shell)

> 2026-09 实测 `www.jiangxisls.com`(DedeCMS,主体系江西赛乐赛医药)。本文件是 SKILL.md §1「四类高价值开发残留」的第 5 类,以及它的守门方式与转身方向。

## 1. 一条请求判定

```
GET /index.php
  -> 200, Content-Type: application/octet-stream, body 以 <?php 开头
```

= 该 vhost **没有 PHP 引擎**。成因:静态化/迁移后 nginx 丢了 fastcgi 段,`.php` 落回静态文件处理,于是整站源码被当文本下发。

旁证(同轮就能确认技术栈):

- `robots.txt` 是 **DedeCMS 默认那一串**(`/plus/ad_js.php`、`/plus/count.php`、`/plus/search.php`… + `Disallow: /include` + `Disallow: /templets`)⇒ 直接确认织梦,不用再猜。
- 全站 `.php` 可读:`/dede/`(后台首页/login/config)、`/plus/*.php`、`/member/index.php`、`/tags.php`、`/templets/default/index.htm`(模板里带 `{dede:global.cfg_webname/}` 等标签)。

## 2. 能拿到什么 / 拿不到什么

**拿得到**:完整源码树、模板、后台入口、字段模型、版本(`$Id: index.php 1 9:23 2010-11-11 tianya $` 这类头部注释直接给版本区间)。

**守门点恰好落在库密上**:织梦的库密在 `data/common.inc.php` —— 实测被单独拦(见 §3),所以「拿到源码」≠「拿到库密」。

**拿不到 shell,别耗**:没有 PHP 引擎 ⇒ 无上传解析、无包含、无框架 gadget;织梦历史 RCE(后台任意文件上传、`/plus/` 系列、`/dede/` 各 payload)全部**要求 PHP 可执行**。把它们在这类站上一个个试是纯浪费。

**正确的转场**:

1. **同主体其它仍有 PHP 引擎的兄弟域** —— 同一张 `*.domain` 证书下的业务系统往往才是真目标(本次家族里就有 TP6.0.9 的 SCRM、TP3.1.3 的媒体广告系统)。
2. **找真源站**绕过边缘规则(源站可能保留 PHP,或至少不带边缘 WAF 规则)。
3. 该主机上的其它服务(端口/管理面)。

## 3. 这类站点的守门方式是「扩展名黑名单」(实测)

同一个 CDN/WAF 上,访问 `/data/common.inc.php`(库密)与 `/data/aaa.php`(不存在)的表现:

| 请求 | 结果 | 说明 |
|---|---|---|
| `/data/aaa.php`、`/data/aaa.txt`、`/data/aaa` | **404**(nginx 548B) | `.php/.txt` 不在黑名单,只是文件不存在 |
| `/data/aaa.inc` | **403**(自定义 11KB 页) | `.inc` 命中黑名单 —— **文件不存在也拦** |
| `/data/common.inc.php`、`/data/config.cache.inc.php` | 403 | 同上,含 `.inc` |
| `/data/config.cache.bak.php`、`/data/backupdata/1.sql`、`/index.php.bak` | 403 | `.bak`、`.sql` 同样在黑名单 |
| `/include/common.inc.php` | 403 | 含 `.inc`(不是 `/include/` 前缀规则) |
| `/include/a.php`、`/include/aaa.txt` | 404 | 证明 `/include/` 不是路径级拦截 |

⇒ **结论:黑名单按扩展名(`.inc`/`.sql`/`.bak`/`.env`),不按目录。** 所以 `.class.php`、`common.func.php` 这类**非 `.inc`** 的文件本来可读,但由于 `include/` 下真正有价值的全是 `.inc.php` 形态,库密依然拿不到。

## 4. 编码/协议变体绕不过:先定性,再停手

同一 payload 的变体实测**全部 403,且 403 页字节数一致**(说明是解码后 URI 匹配):

```
/data/%2Fcommon.inc.php      /data/%2e/common.inc.php     /da%74a/common.inc.php
/data/common.i%6Ec.php       /data/common.inc%2ephp       /data/common%2Einc.php
/data/common%c0%aeinc%c0%aephp   /data%252Fcommon.inc.php  /data//common.inc.php
/./data/common.inc.php       /data/../data/common.inc.php /Data/common.inc.php
/data/common.inc.php?x=.txt  Host 变更 / HTTP/2 / POST    HTTP/1.0
```

**定性方法(一条技巧,省一整轮)**:拿明文与 `%2F` 变体各打一次,若两者返回**同一个 403 页(字节数相同)** ⇒ 规则对解码后 URI 匹配 ⇒ **立刻停手**,不要继续试编码家族。

反例佐证:带尾随字符的变体(`%20`、`%09`、`/`、`;`、`%2500`)返回的是 **404 而不是 403** —— 说明它们**没命中规则**,只是 nginx 按解码后的路径找不到文件。即「规则匹配的是路径本身」,变体无法在不改变路径语义的前提下绕过。

## 5. 真正有效的两个位移

1. **换绝对路径**:规则拦 `..` 类穿越(实测 `?lang=../../` 直接 403),但**绝对路径不受约束**。实测把接口参数从 `path=../../` 换成 `path=/home/wwwroot/<站点>/.env` 就绕过了 `..` 规则(随后卡在应用层鉴权,见 `thinkphp-modern-pentest/references/hg-apidoc-and-debug-oracle.md`)。
2. **换入口**:找不受同一规则约束的其它应用/组件(API 文档、调试接口)来读同一个文件系统。

## 6. 顺手的两条判据

- **目录访问返回统一 3 字节 `dir`**(`/uploads/`、`/data/cache/`、`/data/backupdata/`…)是站长放的占位 `index.html`(用来挡目录列表),`Last-Modified` 是站点维护日 ⇒ **这是收尾痕迹,不是漏洞**,别当发现写进报告。
- **多 IP 同 `ETag` 不是同机证据**:`ETag` = `mtime+size`,CDN 各节点回源同一份文件必然一致。判同机用 `SERVER_ADDR`/phpinfo/内网跳数。
