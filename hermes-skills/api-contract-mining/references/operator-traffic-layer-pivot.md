# 运营流量层：辅助服务 → 剪贴板 → 跳转农场 → TG 频道

适用：主目标铁桶（全 401），但**同源兄弟 IP 上挂着未授权的辅助服务**（状态投屏、剪贴板同步、配置下发）。
这类服务不是漏洞本身，是**运营工作流的实况录像**，一次就把整张资产图交出来。

## 1) 剪贴板/同步类辅助服务 = 情报金矿（本案起点）
- 未授权 CRUD：`/api/list`（全量）、`/api/add`、`/api/delete`、`/api/clear`；CORS `*`；`/download` 直发
  Windows PE（.NET，伪装 `svchost.exe`，写 `Run` 自启，回连本服务）。
- **台账内容比漏洞值钱**：运营的真实后台 URL（`http://<域名>/admin/`）、跳转域名、
  「站点\t账号\t口令\t分组\t负责人\t额度」式投注账号表、代理节点 `IP:端口` + 口令、
  邮箱+口令+手机号、平台内部黑话（「代投工具」「拿官方彩结果来做私盘」「专门的操盘手后台」）。
- ⚠ **探写纪律（本案真实重伤）**：对着写簇发 `DELETE /api/clear`（哪怕空参）会**真清库**（实测清空 148 条运营记录）。
  铁律：① 探测前先**全量 GET 落盘备份**；② 探路只用**自己新建**的条目（`/api/add` 写 marker）再按 id 删自己；
  ③ 永不对辅助服务发 `DELETE`/`clear`/`purge` 类动词。事后须如实交代并保留备份。

## 2) 跳转页与「主机→目的地」映射服务
运营的引流页常是 base64 混淆的一跳：

```html
<script>var _0x=["location","href","aHR0cHM6Ly9uZXhvcmxhdml4LjI3NTEyOS54eXo6ODI4My8/bmI9..."];
window[_0x[0]][_0x[1]]=atob(_0x[2]);</script>
```

- `atob` 后即真落点（本例 `https://<随机>.<数字>.xyz:8283/?nb=<品牌>&bm=<来源>&ml=<线路>`）；
  所有「永久域名」（`kpdz.app`/`cgdz.app`/`4hukp.com`）**同解析到一整段 /24 钓鱼农场**，再各自跳不同前端。
- 另有「**注册主机 → 目的地**」查询服务（FastAPI，`/docs`+`/openapi.json` 全开）：
  `GET /?h=<已注册主机>&p=/` 回 157B 跳转页；`h` 换成未知值/`127.0.0.1`/`169.254.169.254` 只回 123B 加载器页；
  带 `hh=` 回 500。判读：**`h` 是注册表键，不是任意 URL ⇒ 不是 SSRF**，别写成「开放代理」。
- 前排主机的 `/` 是真人页、任意错路径回**伪装页**（实测 `财经网址_360导航上网主页`）⇒ 这是**反爬 cloak**，
  不是「站点挂了/换站了」。取真页要带齐它自己的参数（`nb/bm/ml`、`Referer`、浏览器 UA）。

## 3) TG 频道：从配置里的邀请链接读到运营交易台（只读，不加入）
站点配置（解密后的 `window.CONFIG`）里的 `channel` / `business_cooperation` / `traffic_cooperation`
就是运营的 TG 频道邀请（`https://t.me/+<hash>`）。用现成 Telethon 会话**只读探测**：

```python
from telethon.tl.functions.messages import CheckChatInviteRequest, GetHistoryRequest
r = await c(CheckChatInviteRequest("<hash>"))     # ChatInvitePeek：已用的邀请也能 peek
r.chat.title / r.participants_count / r.about
full = await c(GetFullChannelRequest(r.chat)); full.full_chat.about, .participants_count
```

- **不要为 OSINT 去 Join**；`CheckChatInviteRequest` 就够（标题/简介/人数）。`get_participants` 需管理员权限，
  回 `ChatAdminRequiredError` 属正常，别反复试。
- 频道历史（`GetHistoryRequest`）才是重点：本案是**广告位与流量买卖台**（接 bc/yp/qp/zb、「市场最高价收 seo 量、
  备案米可提供高防 cdn」、「长期收 seo 劫持跳转流量」），并附带永久域名与自家吐槽（「wg 包网被插入 c2，目测有盗 u 风险」）
  —— 直接定性该团伙的业务线与上游供应商。
- 另一类 TG 面在**后台配置里**：管理系统的「系统配置」页暴露 `core.telegram.botToken`/`chatId` 的字段与写接口
  （回显需超管），能证明「该平台有 TG 机器人做开奖推送/结算/告警」，字段名本身即可写进报告。

## 4) 收口顺序（别在铁桶上耗死）
主目标 401 全封时：扫同 IP / 相邻 /24 的端口 → 找**不需要鉴权的辅助服务** → 从辅助服务的台账里取运营资产
→ 解跳转链 → 解前端加密拿 API 与密钥 → 需要凭据时找 `/signup/visitor` 类免凭据端点 → 再用 crt.sh + 子域矩阵扩面。
每一步都把「运营身份」（后台域名、TG、客服链接、邮箱、代理节点）单列一节进报告——这类目标的价值主要在
**组织与资产定性**，不只是某个接口越权。
