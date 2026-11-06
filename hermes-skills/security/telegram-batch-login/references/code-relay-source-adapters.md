# 取码/接码 API 方言与诊断阶梯

做号清单里每号一条取码 URL，凭据形态有三种：路径段 UUID、`?key=`、`?token=`。
**统一抽象**：适配函数返回 `(kind, value, password)`，kind ∈ `code | pending | wait | dead | err`，登录函数只认这几态，新增源只加一个 dispatch 分支。

## 已见方言（判型用）

| 方言 | 响应形态 | 判读 |
|---|---|---|
| JSON 三态（didiapi 系） | `{"msg":"…","status":0}`，`code`/`password` 同层 | `status==0 && code` → **出码**；`status!=0 && msg=="无三十分钟内的登录消息"` → **pending** 重试；`msg` 含「掉线」→ **设备离线**（页面通常带「自助补号」引导，要用户去补号）；`msg` 含「请等待 N 秒」→ **限流**，sleep 后重试；其它 → 判死 |
| 纯文本 `no\|暂无验证码`（62-us 系） | `头\|负载`，无 JSON | 头 `no`/`none` 或含「暂无」→ **pending**；成功形如 `ok|<code>` 或纯数字；多字段时后续字段可能是 2FA 密码 |
| `{"code":0,"msg":"token不存在","data":{"code":"","code_time":"","expired_date":""}}`（tgflare 系） | 结构固定，带 `expired_date` | `token不存在` → token 失效/复制错，**要用户重新取 URL**；`参数不能为空` → 参数名不对或缺参（试 `token`/`key`，补 `phone`）；`data.code` 非空 → 出码 |
| 域名不可达 | 直连/代理/http1.1/tls1.2 全 `000` | 源死。别在它身上继续耗时间——报「域名不可达，需换网络/找服务商」 |

## 取数纪律
- 探针一律 GET 只读，串行 + `sleep 1–3`，别并发轰；尊重「请等待 N 秒」。
- URL 纠错：`https//` → `https://`；`GetHTML` → `GetJSON` —— 同源常同时提供 HTML/JSON 两套，**JSON 版才有可判型的三态**，探针优先打 JSON 版。
- 同一 token 形态在整批号上全废 ⇒ 是 token 层失效，不是单号问题；报「需重新复制」。

## 诊断阶梯（先源后号，别混判）
1. 只读探源 → 死源出局（不发码）。
2. 活源才 `send_code_request`，然后轮询到窗口结束。
3. 只有「发码成功 + 源一直 pending」才算**等码超时**（归因源侧：设备没捕获 / key 与号码不匹配）。
4. 发码阶段就报错 → 归因号侧（封禁 / FloodWait / 格式错），与源无关。

## 全失败时的交付
逐号原因 + 解锁动作清单（补号、换新 token/URL、换网络、等冷却、换号），并附一条可直接粘贴的重跑命令（runner 支持断点续跑）。
