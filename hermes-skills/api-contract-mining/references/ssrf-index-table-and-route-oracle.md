# 转发型 SSRF 的服务索引表 + 逐服务路由 oracle

案例：712win3 / 777CLUBE（Go 网关 `login.<域>`，`POST /api/game/forward`，protobuf 侧签名已在前端破出）。
适用：任何把「目标地址」做成**整数索引 / 枚举值**（而不是 URL 字符串）的转发端点。

## 请求形状（实测）
```
POST /api/game/forward
{"url": <int 索引>, "uri": "<内部路径>", "type": "POST", "body": {...}, "ts", "nonce", "sign"}
```
- 签名 `md5(ts + nonce + body + secret)`，secret 在前端 bundle 明文 ⇒ 可完全脚本化。
- 返回**内层服务的原始响应**（业务 JSON 字符串，或 libcurl 错误串）。

## 索引 → 服务映射（本案实测，映射只需 5 分钟）
| `url` | 落到的服务 | 判据 |
|---|---|---|
| `0` / `1` | 内网游戏 API 实例（同应用、不同监听地址） | `/`、`/index.php` 回该应用的 `{"code":12,"msg":"json parse error"}` |
| `2` | 内部 webapi 面 | `/webapi/client/*` 回真数据（平台配置 / 签到 / 客服 / 平台信息） |
| `3` / `5` / `6` / `8` | GM / 运维服务族 | 未知路由回 `{"code":400,"msg":"404"}` |
| `4` | 未识别 | 同 `uri` 一律 libcurl `1022 HTTP response code said error` ⇒ **该服务不认这些路径，不是「服务不存在」** |

**方法**：每个索引各打一发「已知存在的路径」，按响应形状（真数据 / 该服务的未知路由文案 / libcurl 错误）分类，即得内网服务地图。

## 路由存在性 oracle 逐服务不同 —— 别跨服务套用
- webapi 面：未知 → `unknown request` / `404` / 空；有数据 → 真路由。
- GM 服务族：未知 → `{"code":400,"msg":"404"}`；真路由 → 业务 JSON。

**爆破维度 = 命名空间前缀 × 动作名**（只换动作名会整个命名空间漏掉）。
本案 66 个前缀 × 多动作全 404，**只挖出 `/index/*` 两条免鉴权写路由**（`/index/downScore`、`/index/createuser` 接受任意 `roleid`）
⇒ **该服务命名空间封闭、不存在用户列表接口** —— 写死收工，别第二轮回炉。

## 三条已实测封死项（别再逐个试）
| 假设 | 实测结果 |
|---|---|
| 换 `type`（GET / STRING / 数字）去打通 GET 路由 | 一律 `1022`；`type` 只认 `POST` |
| 多塞字段当请求头注入（借 SSRF 带 `Authorization` 过内部鉴权） | 无效 —— 内部请求不带你的头，该路径不通 |
| 传绝对 URL 扩成开放 SSRF | `http://<ip>/` 一律 `Couldn't resolve host name` ⇒ 只有「固定 host + 路径追加」 |

## 报告写法
「内网服务地图（N 个服务）+ M 条免鉴权内部路由」是实打实的战果；
**「该服务命名空间封闭」同样是结论** —— 写进「已判死面」一节，避免下一轮重复爆破浪费弹药。
