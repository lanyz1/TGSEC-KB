---
name: waf-js-challenge-bypass
description: "WAF JS挑战(node vm执行): 阿里云acw/renderData混淆页."
version: 1.0.0
license: MIT
platforms: [linux]

---
# WAF JS 挑战破解 (node vm 执行挑战脚本)

Use when 目标返回 **JS 挑战页** (非 403/验证码): 阿里云盾 acw (Tengine, Set-Cookie `aliyungf_tc`/`acw_tc`, 挑战页固定 ~110KB 含 `<textarea id="renderData">` 内嵌 JSON + ~75KB 混淆脚本), 腾讯云 WAF (`_waf_<hash>`), 瑞数类。curl 直接请求永远返回挑战页 (HTML), 需执行其 JS 生成放行 cookie。

## 0. 指纹确认
- 响应头: `Server: Tengine` + `Set-Cookie: aliyungf_tc=...; acw_tc=...` + `Punish-Loc: keepper` = 阿里云盾 JS 挑战
- 响应体: `<textarea id="renderData" style="display:none">{"_waf_xxx":"<base64>"}` + 2 个 `<script>` (第一个是 getRenderData, 第二个是 7.5 万字符混淆主脚本)
- **先试廉价绕过再上执行** (各 1 次请求, 全失败才执行 JS): 80 端口 (常 301 跳 443, 无解)、IP 直连 + `-H "Host: <域>"`、`--resolve <域>:443:<IP>`、UA 变体 (curl/空/浏览器) — 实测全回挑战页, 别重复

## 1. node vm 执行流程
1. `curl -sk -c /tmp/cj.txt <目标>/<任意路径>` 保存挑战页 (注意保留 Set-Cookie 的 aliyungf_tc/acw_tc)
2. 提取 `renderData` (textarea 内 JSON) 与全部 `<script>` 内容
3. node vm 沙箱执行: 关键 stub 见下, **脚本执行后等 5-6 秒再读结果** (挑战用 setTimeout/轮询异步完成)
4. 捕获 `document.cookie` (acw_sc__v2 或 `__ac_*`) → `curl -b "aliyungf_tc=...; acw_tc=...; <新cookie>"` 正常请求 API

## 2. 必须的 sandbox stub (缺一个就崩)
```js
// document: getElementById('renderData') 返回 {innerHTML: JSON.stringify(renderData)}
// localStorage/sessionStorage: getItem/setItem/removeItem (脚本会 removeItem 后再 setItem)
// ⚠️ location.replace/assign 必须 return location 对象本身!
// 混淆代码里是 location.replace(x)[...] 链式赋值, 返回 undefined 会报
// TypeError: Cannot set properties of undefined (setting 'href')
// navigator: {userAgent, platform, language, webdriver:false, plugins:{length:5}, mimeTypes:{length:2}}
// setTimeout/setInterval/requestAnimationFrame: 用 node 真实实现 (不是空函数!)
// console: 静默; Date/Math/JSON/... 全传真实实现
```
- 脚本报错时先打印每个 script 的 catch 错误 (别静默吞), 按报错补 stub
- 反 vm 检测: 脚本含 `typeof tl===[]+[][[]]` (node 里 `[]+[][[]]`="undefined") 或 `Function.prototype.toString` 长度检查等 — 撞上后优先转真实浏览器, 别死磕

## 3.5 PoW / hashcash 型挑战（不是混淆页，直接算）

有些自研 WAF 下发的是 **工作量证明**：页面里只有 `ISSUE_URL/VERIFY_URL/WORKER_URL`，worker 就是纯 sha256 循环。这类**不要上 node vm**，直接照抄协议。

实测样本（zx9650.com，2026-10-22）：

```
GET  /v1/challenge/pow/issue   -> {"token":"<JWT>","difficulty":16}
     tid = JWT payload.tid
     PoW: sha256(tid + ":" + nonce) 前 difficulty 个 bit == 0
POST /v1/challenge/pow/verify  {"token":t,"nonce":n,"returnUrl":url} -> {"ok":true} + Set-Cookie ct_pass
```

```python
h = hashlib.sha256((tid + ":" + str(n)).encode()).digest()
if int.from_bytes(h[:4], "big") >> (32 - dif) == 0: break   # dif<=32 够用
```

- 难度 16 bit ≈ 1.2 万次（0.03–0.2 s），20 bit ≈ 100 万次（~1 s）——**纯 Python 足够，无需多线程**
- 重复挑战会**升难度**（16→20），所以拿到 cookie 后要批量把目标请求打完
- cookie 通常 30 分钟；同 IP+UA 直接复用
- 判据：403 body `{"message":"challenge required","challengeUrl":"/...challenge?returnUrl=...","code":40301}`

## 3.6 备选路径 (stub 修不动时)
- **真实 chromium 无头**: `chromium --headless=new --no-sandbox --disable-dev-shm-usage --user-data-dir=/tmp/cdp --remote-debugging-port=9222` 过挑战后 CDP 拿 cookie; ⚠️ 低配容器 (pids.max 紧/线程受限) chromium 起不来 (GLib `g_task_thread_pool_init` 失败 / pthread_create EAGAIN) — 先看 `/sys/fs/cgroup/pids.current` vs `pids.max`, 余量 <100 别试
- **找无 WAF 旁路**: 同 IP 反查 (fofa) 其它域名/端口; 同源静态托管 (GCS/OSS 前端) 无 WAF 但 API 域名全 WAF 时, 看是否有备用 API 域名 (前端 JS baseURL 里常藏着 2 个: int.xxx601.com / int.xxx602.com, 都挡就无解)

## Pitfalls
- 挑战页大小是固定指纹 (阿里云 acw = 110310B, `_waf_bd8ce2ce37` 前缀每次不同但页面结构同) — 同款 WAF 破解一次, 脚本可复用 (只换 renderData)
- 挑战 cookie 有有效期 (acw_tc Max-Age=1800 级别), 拿到后尽快用, 可批量把 API 请求打完再过期
- 别对挑战页跑目录扫描/注入 — 那只是 WAF 壳, 浪费时间
- 本 skill 记录的方法 2026-08-06 在 int.rryl601.com (170.33.12.118) 上已验证流程与坑, 但**尚未完整跑通拿 cookie** (卡在后续反 vm 检测); 跑通后请回来补成功模板

## 真源

- 手法：`docs/playbooks/对抗规避手册.md`
- 工具：`python3 tools/ops/waf_detect.py --help`
