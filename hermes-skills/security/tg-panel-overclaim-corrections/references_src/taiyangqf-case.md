# 案例：taiyangqf.com（64.118.128.47，2026-09-05）—「云控群发系统/tg6kong代发」

NestJS+React+antd 租户面板，仅 22/80/443，nginx/1.24，域名 2026-08-25 注册（11 天新站），日发送 205 万条（重生产）。

## 1. 定性纠正全过程（本案例核心价值）

**初报（过度定性）**：send-code→verify→「响应含 StringSession」→telethon 重建→`authorized: True` → 写成「★ TG 会话接管闭环」。

**用户当场纠正**：「什么玩意？这不是把我自己的账号上传又导出吗？」——完全成立：verify 回传的 session 是**我自己测试号**（ceshi52 租户入池，@niwquz 8942050063）的流程内材料。入池本就是业务设计，属主拿回自己的 auth_key 无越权增量。

**复核动作（probe19/20 差分矩阵实测）**：
| 测试 | 结果 |
|---|---|
| 列表 fuzz（grouped/accounts + scope=all/ownerUserId=all/includeAll=1/keyword/limit） | 恒只回自己账号 |
| detail / two-factor-status × fabricated ID | 统一 403「啊哦，有点问题」= 无存在性 oracle |
| worker 动作 × fabricated ID | spambot/kick 404、rotate 403（先查存在→404；rotate 有角色守卫→403） |
| bulk 混入 [OWN+RND] | 201 total:1，RND 被静默过滤 |
| bulk-task/{任意ID} | 200 null = 任务 ID 存在性 oracle（唯一低危残留） |
| /groups/{RND} | 404 Cannot GET 透传（无分组控制器伪装） |

**终版定性**：§3.1 降级为中危「auth_key 直出浏览器 = 钓鱼放大器」（诱导他人在面板登录即持永久凭证，对受害者侧有意义，对租户侧无越权）；跨租户隔离完好。

**教训**：headline 定性必须在跨租户差分**之后**发布；先报后验=被用户抓过度定性。

## 2. 275B 自定义 StringSession 布局（逐字节）

- 标准 telethon StringSession=353B；本平台 275B，`StringSession()` 报 `unpack requires a buffer of 275 bytes`
- b64 对齐扫描：offset 0 无 ASCII IP、offset 1 命中（b64 跳过首字符后解码）
- 布局：`[1B dcId?] [12B ASCII "91.108.56.150"] [2B port BE=443] [256B auth_key]`，无尾料
- 重建（livetest2.py 实测 authorized:True）：
  ```python
  from telethon.sessions import MemorySession
  from telethon.crypto.authkey import AuthKey
  sess = MemorySession(); sess.set_dc(1, ip, port)
  sess.auth_key = AuthKey(bytes.fromhex(key_hex))   # 必须 AuthKey 对象
  ```
- api_id/api_hash 用哪个都能连（本地参数不参与远端校验）；本例平台泄露 loginApiId=9/apiHash=3975f648bb682ee889f35483bc618d1c（「群发端口」，跨租户可见=真严重级漏洞）

## 3. 真实漏洞清单（终版）
- 【严重】平台 TG apiHash 跨租户泄露（verify 响应 loginApiId/loginApiHash 字段）
- 【高危】未认证越权读矩阵：/proxies/pools（3 池 8 出口 IP：149.119.166.48/204.0.11.51/204.0.10.108/38.111.18.25/38.75.201.5:443 + 202.58.107.34-36:1080-1082）、/regions（美国节点池 3 节点 capacity 47424 + 运营者 userId cmkoocr6n0008cmwu8zy3jfyf）、/stats 平台级 205 万条/日
- 【高危】验证码 SVG `<text>` 明文答案 + 无登录限速
- 【低危】monitor slug=登录 ID（JS 回退链 monitorSlug→loginId→email，实测 slug=ceshi52）；有效租户监控页匿名可旁观群发/加群记录（30s 轮询）；统一 404 文案无枚举 oracle
- 【信息】GET /api/system-notice 全局公告「沙县小吃月球总代理」（认证可读，匿名 401）

## 4. 面板防护强项（勿重复撞墙）
写端点全局守卫（self-PATCH 都 403）、JWT HS256 强密钥（wallarm 10.4 万词未中）、zip-slip 防护、伪 session 正确判 failed、上传类静默 429（690s 窗口）、Pydantic 严格 DTO、socket.io 不存在（SPA fallback 假 200——判断实时面先看 HTML 是否回 index）。
