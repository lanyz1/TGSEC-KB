# 家族平台溯源：管理端契约 / 供应商面 / 探测纪律

本卡记录 `myqb`（MYPay 红包钱包）家族的**管理端与供应商面**——这些结论跨实例复用，但**判定同源必须看框架指纹**。

## 1. 家族管理端 = vue-element-admin + `/prod-api` GET API（★ 可直接复用的词表）

供应方公开仓库 `github.com/yishellmeta/telegram-red-vue-manager`（实装版 vue-element-admin v4.4.0，266 文件）+ `telegram-red-admin`（README = 红包机器人官方说明：发包 `50-4`/`50/4`、抢包需余额≥1.8×、中雷赔付 1.8×、平台抽水 5%、抽水 35% 返上级、开公群需机器人管理员、**用户余额只能在后台人工充值**）。

`.env.production` → `VUE_APP_BASE_API = '/prod-api'`；接口**全 GET**（`src/api/*.js` 里 `method: 'get'`），38 个真实端点：

```
/prod-api/login  /userList /deleteUser /updateUser /userFlowList /orderList /orderInfo
/topOrderFlowList /withdrawFlowList /rechargeFlowList /addRecharge /addWithdraw
/shenheWithdraw /outApply /configList /updateConfig /menuList /adminList /addOrUpdateAdmin
/groupList /addGroup /deleteGroup /bobmUserList /addBobmUser /deleteBobmUser
/autoGetUserList /autoGetUserAdd /autoGetUserDel /userNodeAccountDes /updateUserNodeAccount
/userPushList /userRechargeAddressList /userRechargeAddressKeyInfo /userWithdrawAddressList
/saveOrUpdateShow /admin/alternately/{list,create,click,out,not,out,is_out,vote_out,update,tabulation}
```

探测时**两个前缀都要试**（`/prod-api/<X>` 与 `/<X>`），**方法按契约用 GET**，并带上（可选）`/dev-api`。

## 2. 判同源：框架指纹优先于路径特征

- Go/Gin：`404 page not found`（**18 字节**）
- FastAPI：`{"detail":"Not Found"}`（**22 字节**）
- 同一 API 基路径（如 `/api/miniapp/v1/`）**不等于**同一个后端：`yibeitech.cn`（供应商「轶贝/亿贝」基建机 `139.227.11.186`，Harbor v2.10.1 + FastAPI「直播选品投票」）与小程序的 Go 后端共用约定但**不同框架**，据此排除同源。

## 3. 供应商面（勿越界，只做只读取证）

`139.227.11.186`：`:8443`/`:8888` TLS（证书 `CN=*.yibeitech.cn`）、`:11000` 小米路由器、`:11080` Harbor（公开项目仅 `lib`/`library`/`rancher` 基础镜像；**平台镜像在私有项目**）。判断标准是「是否属于**攻击目标本体**」；供应商侧只用于获取软件契约（等同其公开文档/公开仓库），不发起攻击。

## 4. 准入探测纪律（本轮踩坑）

- ★ **SPA catch-all 站点做路径探针前必须跑负控**：随机路径 GET 若回 200 + 同一 HTML（如 728 B SPA），说明该主机 GET **无判别力**，满屏「命中」全是兜底假象。真路由会返回 JSON（哪怕 401）。
- **任何「0 命中」结论必须有正控**（已知路由→已知错误码，如本目标 `POST /api/miniapp/v1/handshake` → `401 {"code":40701}`）+ 负控（随机路径→404/兜底）。
- Censys 匿名**每日 5 次**：字段用 `host.services.cert.names` / `host.services.endpoints.http.body` / `…html_title`；先跑正控（如 `cert.names: "github.com"`）证实 oracle 有效，再用 `cert.names: "<目标域>"` 作负结论。**body 索引是找同族实例的杠杆**。
- CT 只有通配证书（`*.yibeitech.cn`）时被动子域枚举无门 ⇒ 改 DNS 爆破；反之 `myqb.io` 无通配 ⇒ 被动枚举即可穷尽。

## 5. 实测：DNS 爆破与「同族站交叉引用」判部署（两者都做完可结题）

**DNS 爆破（先跑随机名做基线，NXDOMAIN 才说明名单完整）**
- `myqb.io` 无通配 ⇒ 全词表只出 **2 台**（`redpack` / `mch`，均 CF）⇒ **管理端不在 `*.myqb.io`**（定论）。
- `yibeitech.cn` 无通配 ⇒ 4 条真实记录：apex `212.64.102.24`(UCloud)、`ops` `139.227.119.39`、`crm` `47.100.6.147`、`monitor` `101.132.161.7`（供应商运营/CRM/监控三件套，属供应商面不动）。

**同族站交叉引用法**（判「同族站是否与目标同一部署」）
1. 收集候选（同族域名/裸 IP）；2. 取各站首页 HTML；3. 抽出其静态资源 URL；4. 比对是否引用**目标域**资源。
- 命中 ⇒ 同源部署（可顺藤摸源站）；**全 0 ⇒ 弃线**（本例 8 个候选全 0，含 `api.redpocketzziu.com` 3239B/4 资源 ⇒ 与目标非同一部署）。

## 6. Telethon 驱动 bot 控制台：必须「当前消息 msg_id 绑定」

```python
mm = await cli.get_messages(ent, ids=cur_mid)          # 读回当前那条消息
btn = <从 mm.buttons 里按 data 原样取出>              # data 不可猜
await cli(functions.messages.GetBotCallbackAnswerRequest(peer=ent, msg_id=cur_mid, data=btn.data))
```
- 猜 `data`/`msg_id` ⇒ 全量 `DataInvalidError`（`mqvas.py` 的失败）。正解范式见同目录 `mqnav4.py`。
- 根菜单真实 data：`menu_recharge/withdraw/transfer/receive/redpacket/merchant/profile/swap/yuebao/vas/gamecenter/language`；二级如 `vas_orders:all:1`。
- session 被多客户端并发使用 ⇒ `MsgidDecreaseRetryError` 刷屏；跑前用**独立 session 副本**并清理遗留 python 进程。
- ★ Windows 坑：给原生 Python 的路径一律 `C:/...`；`$PWD` 展开成 MSYS `/c/...` 会导致 `sqlite3.OperationalError: unable to open database file`。

## 7. ★ 两条「先验证再下结论」铁律（都是被假阳性敎过）

**a) 多账号对比 ⇒ 必先证账号唯一**：不同 session 文件≠不同账号。先打印 `me.id`（同一 id = 同一账号，结论自动作废）。
- 反例：`acc1..acc4` 四个 session 全是 `8407222813` ⇒ “4 账号共用同一充值地址”是假阳。
- 正解：找**两个真相不同**账号（本例 `8407222813` vs `8664154553`）分别读充值地址 ⇒ 结果为**不同的专属地址** ⇒ **否定了「共享地址 + 按 from 归属劫持」类缺陷**（负结论已写报告）。

**b) 链上地址 ⇒ 必过 base58check 再用**：裸正则 `T[1-9A-HJ-NP-Za-km-z]{33}` 会大量命中 **base64 片段**（API 返回 400 = 非法）。
- 正解：正则 + double-sha256 前 4 字节校验；脚本见 `traddr.py` 写法（零网络、只读本地）。
- 链上判定须带**正控**：USDT 合约地址跑同一端点能回 50 笔/12 from ⇒ oracle 有效，此时目标地址 `200/68B=[]` 才能判为“0 笔”。

**c) 双账号实测结果（本家族现状）**：平台**按用户独立生成专属充值地址**（A≠B，且两者链上均 0 笔未启用）；支付密码是提现类资金动作的闸门（首页明示未设置）。

**d) bot 控制台遍历：每根键一次 `/start` 复位**
- bot 会**重写同一条消息的键盘** ⇒ 在同一 msg_id 上连点多次后，后续键会“消失”，看上去像**平台拦截**（假象）。
- 正解：`/start` 复位 → 在新 mid 上只点一次 → 采页面；脚本 `mqnav5.py`（EXIT=0，全根键走完）。
- 实测功能图（账号 B）：首页/充值(Tron 地址，TON 不可点)/提现·转账(🔒支付密码)/收款(rc_cur)/红包(rp_flt)/**商户(mrch_create)**/个人中心(pf_bal)/闪兑/余额宝(年化5%)/**增值服务(vas_prod:stars = 代充 Stars/Premium)**/游戏中心/语言。
- ★ 控制台内**无任何 Web 后台 URL**（只有 t.me/myqbchannel）⇒ 管理面不在客户端可见面。
- ★ `mrch_create`（自建商户）= 对 `mch.myqb.io`（Go 纯 API，无 oracle）**取认证的合法入口**：拿商户凭据后可做带认证只读调用再测越权/回调/幂等。属写动作且可能带费用 ⇒ **需作者明确授权再执行**。

## 8. ★ 三条探针伪影铁律（本目标连踩三次，已四次修正）

**a) `curl` 的 `0/0B` 不是证据**：它 = 连接被丢/超时（速率、代理、CF 都可能），常出现在“连续快速请求”的靠后几条上。
- 实例：`mch POST /api/v1/merchant/callback` 等被早期脚本标为「★ 命中」，复验（负控 + 同类假名对照 + 每项 2 次 + 间隔 1.5s）后**全部其实是 `404/18B`** ⇒ 无路由。
- 规则：任何非预期响应码/零字节，必须**同时有负控与同类对照、重复 2 次、带间隔**才允许定性。

**b) 探针未跑完就取文件 = 假“截断/卡死”**：`jump_run exec` 不等远端进程结束。
- 正解：远端脚本顶部 `exec > /tmp/x.out 2>&1`，末尾打 `=== DONE ===`，本地**轮询** `get` 直到见到标记。

**c) `405 nginx` ≠ 应用层路由**：先判该 location 是静态/SPA 还是反代应用。
- 实例：redpack（GET 是 SPA 兜底 200/728）对所有 POST 回 `405/550B nginx` ⇒ **对 redpack 的 POST 无判别力**；这也解释了 `/callback`、`/notify`、`/admin-api/v1/*` 的“命中”全为伪影。

**d) 判 `mch.myqb.io` 现状**：全路径 `404/18B`（含负控），无有效 oracle ⇒ 要 oracle 必须走**带认证**（商户身份）。

## 9. ★ miniapp 鉴权定论：**handshake 需 initData**（「免凭据建会话」己证伪）

实测（bj，无凭据，零副作用）：
```
POST /api/miniapp/v1/handshake   -> 401 63B {"code":40701,"message":"登录状态无效，请重新打开"}
POST /api/miniapp/v1/rp/handshake -> 404 18B  404 page not found
```
- ⇒ **ECDH 会话建立在鉴权之后**（`X-Telegram-Init-Data` 必须在）；**会话 ≠ 鉴权**；`/rp/handshake` 路由**不存在**。
- ⇒ miniapp 面所有后续测试（`rp/open`、`rp/claim`、`rp/verify-segment`、`user/*`）**必须先有合法 initData**；否则只有 `401/40701`。
- `401/40701` 是该 API 的**正控标志**（探针自检用）。

**工具链**：`jump_run.py exec` **实测会回传 stdout+stderr**，但长输出可能截断/脚本可能未跑完 ⇒ 仍要远端 `exec > /tmp/x.out` + `=== DONE ===` + 轮询取回；远端脚本必须空值兜底（`hd = hd or {}`），否则 None 崩溃会掩盖全部诊断信息。
