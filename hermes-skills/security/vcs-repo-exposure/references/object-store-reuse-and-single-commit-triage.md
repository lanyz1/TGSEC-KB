# 对象库的二次利用 & 单 commit 止损

来源:fm.jiangxisls.com 实战(2026-09-14)。前提:`.git` 可读、`git-dumper` 不通、无目录列举、每出口请求数要省。

## 1. 单 commit 判定 = 最快的止损点

`GET /.git/logs/refs/heads/master`(reflog)只有一行 `commit (initial)` ⇒ 仓库只有一次提交。

⇒ **`.gitignore` 里的东西(`db.php` / `config.php` / `Upload/` / `Runtime/`)永远不在对象库** ⇒ 立刻停止寻找"历史版口令/被删文件",这条路在 git 层面就不存在。

**0 请求自查法**:解析出 index 清单后,先在本地 grep 目标路径(`db.php`、`config.php`、`*.sql`、`*.xls`),**有命中才去花请求取 blob**。
本次实测:`App/Conf/db.php` 不在 index(被 gitignore)⇒ "DB 直连凭据确实无源"这句结论可以写实,不用再试探。

## 2. index → blob 直取(比走 commit→tree 快得多)

- `.git/index` 每条 = `62 + len(name)` 字节,**blob SHA 位于条目内第 41-60 字节**(40 字节固定头之后)
- 续真:`pad = 8 - total % 8`,**整除时补 8 而不是 0**(错了会只解析出零头条目)
- `GET /.git/objects/<sha[:2]>/<sha[2:]>` → `zlib.decompress(raw)` → `b"blob <size>\0<content>"`
- 实测 4224 条全部解析成功,**单个 blob 一次请求即得**,不需要 packfile、不需要列举 objects 目录(目录列举通常被 nginx autoindex off 挡掉)

把清单落盘成 `name<TAB>sha` 的文件,后续取哪个文件就 grep 哪个,不用重算。

## 3. ★框架源码也要取 —— 用它"定语义",别凭版本常识猜

应用源码里发现可疑注入/可疑上传时,**把该站点自带的框架/库源码从对象库取回来读**,比猜版本行为可靠得多:

- `ThinkPHP/Lib/Core/Model.class.php` → `limit()` / `count()` / `parseWhere` 的真实实现
- `Public/plugins/<editor>/php/Uploader.class.php` → 该站**真实生效**的扩展名白名单与文件命名规则

本次即靠它拿到决定性事实:
```php
public function limit($offset,$length=null){
    $this->options['limit'] = is_null($length)?$offset:$offset.','.$length;
}
```
⇒ `limit(false)` 生成 **空 LIMIT**(字符串化后为空),配合 payload 末尾 `#` 可把该子句注释掉 —— 这类事实靠猜是猜不到的。

⇒ 修正一条常见偏见:**"框架/vendor 目录对拿凭据没帮助"** ≠ "框架源码没价值"。拿凭据跳框架,**定语义必须读框架**。

## 4. 判别器:应用错误页 ≠ nginx 404

有的部署是 `RewriteCond %{REQUEST_FILENAME} !-f` 再丢给入口文件,于是:

| 情况 | 响应 |
|---|---|
| 文件存在、是 `.php` | 直接返回(**被执行**,不吐源码) |
| 文件不存在 | **应用自己的错误页**(如 TP3「无法加载模块:.git」) |
| 前缀被 deny | nginx 自己的 403 页 |

⇒ **看到应用错误页 = 该路径没被 deny,只是文件不存在**,别再往"被 WAF 拦了"上归因、别再试编码绕过。
形态识别:同一个仓库里 `/.git/index` 能 200、`/.git/HEAD` 却是应用错误页 —— 就是这个组合。
