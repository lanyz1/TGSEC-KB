---
name: dokuwiki-draft-race-object-injection
description: "Use when testing DokuWiki draft race to RCE."
---

# DokuWiki 草稿竞争 → 反序列化对象注入 → 任意文件写 RCE

## 一句话
DokuWiki 的草稿保存/读取用 `fopen('wb')`（O_TRUNC）且不加读锁。并发写两份草稿 + 高频读草稿，`io_readFile()` 会读到 `A[:n] + B[n:]` 的拼接串；`unserialize()` 反序列化出攻击者对象。用 `MemoryIndex` gadget 写 webshell；老版本用 `Installer` gadget 删配置 → `/install.php` 重装 → 插件 RCE。

## 前置
- 有可写账号：`AUTH_CREATE` 权限（或匿名 `* @ALL 4`）。
- `$conf['usedraft'] = 1`（默认开）。
- 目标版本：MemoryIndex gadget 自 **2026-07-14** 起存在；Installer gadget 自 2014-05-05 起（老站可打）。
- 草稿目录 `data/cache/<bucket>/<md5>.draft`；需知道或猜 `$conf['cachedir']`（常见 `data/cache`）。

## 原理
- `saveDraft()`：`serialize([...])` 后 `io_saveFile($file, $body)`；`io_saveFile` 用 `fopen($file,'wb')`，O_TRUNC 但**不锁读**。
- `getDraftText()`：`unserialize(io_readFile($file))`，无 `allowed_classes=false`。
- 两份草稿 A/B 长度对齐，使注入的序列化对象在拼接串里完整出现一次：`A` 的前缀 + `B` 的对象 + `A` 的后缀，或反之。
- 读请求在 truncate 与写完之间命中，就会看到 `A[:n] + B[n:]`。

## Payload（MemoryIndex）
`dokuwiki\Search\Index\MemoryIndex`：
- `filename` = 目标路径（默认 `/var/www/html/lib/plugins/shell.php`）
- `isWritable` = `b:1`
- `data` = `[code => '<?php ... ?>']`
- `dirty` = `b:1`
析构时 `save()` 走 `io_saveFile` 写出 webshell。

## 利用
公开 PoC：`gist.github.com/sebastianosrt/a0c0252ca335e8e8b2c96fecf1f64538`（Python aiohttp + uvloop，含两个 gadget 的完整序列化串）。
```bash
python3 doku.py --url http://target/dokuwiki --user u --pass p \
  --shell /var/www/html/lib/plugins/shell.php
```
参数以 gist 为准；默认 4 writers / 20 readers、2 并发攻击、600s 超时、轮询 shell。

## 注意
- 没开草稿/没 AUTH_CREATE 打不了；先 `POST lib/exe/ajax.php` 的 `do=draft` 看是否 200。
- 竞争窗口窄：先本机/同网段低延迟打，别跨洲；必要时加 writer/reader。
- 路径必须 web 可写且可执行；`open_basedir` 下换 `data/` 或插件目录。
- 写 shell 会留痕；测试后删除，别把客户 wiki 打挂。
- 同一 bug 的 Installer 变体是删文件→重装→插件上传，适合老版本，但破坏性更大。

## 修复
`unserialize($body, ['allowed_classes' => false])`（或 `json_decode`）；升级到包含该修复的版本；禁用草稿或限制 `AUTH_CREATE`。
