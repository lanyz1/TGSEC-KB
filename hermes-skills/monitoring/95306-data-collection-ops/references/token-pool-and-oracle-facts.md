# 95306：凭据池位置 + 判活/退出 oracle（探针取证口径）

## 路径事实（别猜路径，先按表定位）

| 想找什么 | 真身 | 说明 |
|---|---|---|
| 票池（ST / jwt 票） | `/opt/v6/bid2_tokens.json` | `{"jwt":{tok:rec},"st32":{tok:rec}}`，每条带 `tm`（北京时间）；**按 `tm` 排序即得龄期分档的采样源** |
| collector 状态里的 `rail_pool` | `store.py` 侧（`grep -rn rail_pool`） | **不是** `/opt/v6/v6_state.json` —— 该路径不存在，旧脚本里写了也别照抄 |
| 账号↔企业 | `/opt/v6/acct_map.json`（索引，含 `ent_full` / `pack_map` 计数）+ `/data_pool/ent_registry.json`（`{信用代码:{企业全称:{first,last,n}}}`） | `/data_pool/acct_map.json` **不存在**（极容易误拼）。`ent_registry` 的 `last` = **我方采到该企业记录的最后时间** ⇒ 判「某项目缺企业明细」是机制边界还是采集 bug，首选这条证据（若该企业 `last` 远早于项目在网时间 ⇒ 我方从未采到它，等票而非修代码） |
| 名录 | `/data_pool/plat_enroll_map.json` | `sync_plat_enroll.py` 产，`bot/pool.py:172` 消费 |
| 缺口（治本产物） | `/opt/v6/gap_projects.json` | `gapgen` 产；三数口径「在网项目 / 缺企业 / 缺账号」 |
| 采集机票文件 | CN 机 `/opt/v6/bid2_tokens_cn.json` | 淘金器 `audit_harvest_cn.py` 产；主控 relay 拉平 |

## 判活三态（实测口径）

打**只读**端点 `GET /business-proxy/business/user/info`，头 `Authorization: <st32 票>`：

| 响应 | 判读 |
|---|---|
| `200` + `"success":true` + 账号实名/单位字段 | **活**，可读业务数据 |
| `200` + `系统服务异常 code=100`（`data:null`） | **鉴权通过、账号侧异常** —— ★**不是失效**；同一枚票数分钟内可在两态间抖动，且与票龄**无关** |
| `401` + `未登录或已退出登录` | **失效**（唯一可用判据） |
| `500` + `您没有该功能的操作权限` | 路径不在路由表（**基线响应**） |

- **票 TTL 远长于采集周期**：按 `tm` 分档（<1h / 1-6h / 1-3天 / >7天）采样，8/8 全部过鉴权、0 失效；最老样本 **11.36 天**仍 `200`。
  ⇒ 「6 小时」是**刷票/采集节奏**，不是票寿命；不要据此丢弃老票。
- **采集侧判死只认 401**：以 `success:true` 为唯一活性判据会把中间态活票误判为死票（票池被白清、重复补票）。

## 退出（logout）契约：现状与正确姿势

- 候选 8 条（**全部** `401 未登录或已退出登录`）：`/user/logout`、`/user/loginOut`、`/user/logOut`、`/user/exit`、`/user/quit`、`/user/offline`、`/user/loginout`、`/login/logout`。
- **零副作用基线**：有效凭据打**不存在路径** ⇒ `500 您没有该功能的操作权限`。候选与基线**不同号不同句** ⇒ **弱正向线索**（这组路径在网关层有独立鉴权处理，可能真实存在），
  但 401 出在鉴权层，**据此定论不了**。
- **「用已失效票探 logout」的设计不可行**：池内票全为有效（见上方 TTL），拿不到失效样本。
- **活票打 logout = 有真实副作用**（会让真实企业账号在平台侧掉线，报名期尤甚）⇒ **须用户明确点头**才做；只发一枚、事后核该账号能否再登录。
- 探针脚本（`/tmp` 可复跑，均只读、串行限速）：`st_exit_probe.py`（采样+契约）、`st_exit_probe3.py`（修龄期符号 / 打原始 body / 基线校准）、`st_ttl_probe.py`（分档 TTL）；
  产物 `st_exit.json` / `st_exit2.json` / `st_exit_ttl.json`。

## 工程含义（可直接落进采集/agent 逻辑）

- 票池清理、`apply_*` 闸门、AI 侧取数判断，一律以「**401 = 失效**」为唯一下线判据；`code=100` 只能当「本次取数失败，可换票重试」。
- 判「某企业明细为何缺」的次序：① `ent_registry.last`（我方是否采到过）② 该企业账号有无票 ③ 才是代码侧缺口腿（`gapgen` / `gapstock` 死区）。
