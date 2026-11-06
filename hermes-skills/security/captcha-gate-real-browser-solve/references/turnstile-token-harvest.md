# Turnstile token 取用（headed + 多出口）

## 失败现象对照表（先查这张表，别乱改参数）

| 现象 | 结论 / 动作 |
|---|---|
| `typeof window.turnstile === 'object'`，`getResponse()` 空，页面 `iframe` 数 0 | **headless 静默失败** → 换 headed 实例 |
| headed，但直接 `goto` 受控页 URL → token 仍空 | SPA 初始化没跑 → 改走站内导航进入 |
| headed，自己 `turnstile.render(div,{sitekey})` → widget 建出来了但永不回调 | 自建 widget 挂起 → 借站点自己的渲染路径 |
| headed + 站内点入口进表单 → 5~10s 出 token | 正常，token 长度数百字节 |

## 最小 harness（Playwright 连 CDP 实例）

```python
pg.goto(HOME, wait_until="domcontentloaded", timeout=90000)   # 先站内首页，不是表单页
time.sleep(6)
pg.evaluate("""(()=>{const e=[...document.querySelectorAll('a,button,div,span')]
  .filter(x=>x.textContent.trim()==='<入口文案>'); if(e.length) e[e.length-1].click();})()""")

tok = ""
for _ in range(20):                                            # 必须轮询，只查一次会假阴性
    time.sleep(1)
    tok = pg.evaluate("(()=>{try{return (window.turnstile&&window.turnstile.getResponse())||''}catch(e){return ''}})()") or ""
    if tok:
        break

# 同页立刻发请求（同源 fetch，带自定义头也不触发预检）
pg.evaluate("""(async()=>{const r=await fetch('<API>',{method:'POST',credentials:'include',
  headers:{'Content-Type':'application/json'},body:JSON.stringify(<BODY>)});
  return {s:r.status,b:(await r.text()).slice(0,300)};})()""")
```

- `<入口文案>` 用站点自己的导航字面量（「登录」「Sign in」…），匹配多个时点**最后一个**（通常才是导航栏那个）。
- 请求体里的 token 字段名从调用点取（常见 `captcha_payload.turnstile_token`），别照表单 DOM 键名猜。
- token 一次性、TTL 分钟级 ⇒ 取即用，不落盘、不写报告正文。

## 多出口要点

- 每个出口一个独立实例：
  `chrome.exe --remote-debugging-port=<9226+> --user-data-dir=<独立 profile> --proxy-server=socks5://127.0.0.1:<端口>`，**必须 headed**。
- profile 目录每实例独立（运行中实例的 profile 有单实例锁，不能复用）。
- 产物**可能**与该出口绑定（服务端把 ClientIP 当作 `remoteip` 传给 siteverify 时）⇒ 保守做法是出口↔实例 1:1，
  **不要**「本机取 token、别处发请求」。
- 出口的额度记账与轮转调度见下节。

## 出口矩阵：先量测，再轮转

```bash
# 1) 先只列在听的本地 inbound 端口（不要一上来扫端口段）
netstat -ano | grep -i LISTENING | grep -oE '127\.0\.0\.1:[0-9]+' | sort -u -t: -k2 -n
# 2) 只对在听的端口逐个测出口 IP，短超时
for p in <端口列表>; do ip=$(curl -s -m 6 -x socks5h://127.0.0.1:$p https://api.ipify.org); echo "$p -> ${ip:-FAIL}"; done
```

- 本地代理客户端（v2rayN 之类）常同时开多个 inbound，**每端口一个不同出口 IP** —— 最便宜的轮换源，不依赖外部代理池。
- 现成的**全端口段矩阵脚本会去连大量未监听的端口而挂死（>300s）** ⇒ 先用 `netstat` 收窄端口集再探，一轮十几秒出结果。
- 两个端口挂同一节点很常见（出口 IP 重复）⇒ **先按 IP 去重**，再算总配额。
- **额度按出口记账**：实测同一发请求在未用过的出口返回业务响应、在主出口返回 429 ⇒ 换出口即重置。
- 调度 = 每出口配额 ÷ 冷却窗口 → 总吞吐（例：2 次/900s × 8 出口 ≈ 64 次/小时），按最早可用出口轮转；
  **批量前先向用户要授权**，并给出 出口数 × 配额 → 吞吐 → 总耗时。
- 伪造 `X-Forwarded-For` / `X-Real-IP` 绕不过这种限流：CF 会覆盖/追加，应用侧 `ClientIP` 仍取真实 IP ⇒ 只能换真出口。
- 仓库代理池（大量节点 + 分类/测速命令）是另一条并行通道，见用户自有卡 `egress-proxy-pool`。
