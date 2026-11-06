# 案例课：wefe.cc 商城 — `.action!method` 零凭据三层拖库 + `type=1` 破脱敏

> 来源：报告包 pack-20261022（2026-10）· 域：api-security

## 一句话

老 Java 商城用 `*.action!method` 风格路由，评价/订单/卖家三层接口**全部零凭据**；关键一刀是订单接口加 `type=1` 走"内部视图"跳过脱敏，直接回明文 PII。用 `partyId` / `sellerId` 把三张表缝起来，7,873 买家真名+邮箱+手机+完整街道、196 卖家含 87 份签署合同 PDF 全量落地——服务器 RCE 与后台接管都没破，但第二目标（全量数据）100% 达成。

## 链

| 步 | 接口 | 参数 | 产出 |
|---|---|---|---|
| ① | `/api/evaluation!list.action` | `pageSize=50&pageNum=1..1055` | 52,694 评价 → 52,602 orderId + 7,873 partyId |
| ② | `/api/order!info.action` | `orderId=<X>&type=1` | **明文 PII**（`type=1` 绕脱敏） |
| ③ | `/api/seller!list.action` | `pageSize=50&pageNum=1..11` | 196 sellerId |
| ④ | `/api/seller!info.action` | `sellerId=<X>` | 卖家全字段 + `signPdfUrl` |

缝合：`partyId` 关联 评价→订单→买家；`sellerId` 关联 卖家→商品。评价表是入口，因为它同时带 `orderId` 和 `partyId`。

## 判据

| 现象 | 含义 |
|---|---|
| URL 形如 `/api/xxx!list.action` | Struts2 风格 `!method` 路由，方法级鉴权常缺失 |
| `type=1` / `view=internal` / `isAdmin=1` 切换返回字段变多 | 内部视图开关，脱敏只做在默认分支 |
| 列表接口回 `pageNum/pageSize` 且无总数风控 | 可直接遍历全量，无需注入 |
| `signPdfUrl` / `contractUrl` 直出 | 合同类 PDF 可批量取 |

## 三目标终局（可复用的定性模板）

| 目标 | 结果 | 依据 |
|---|---|---|
| 服务器 RCE | ❌ | 5 个写入点全阻塞；SQL 58 载荷 / 命令注入 20+ / 反序列化 / 默认密钥 / 备份文件 455 路径全排除 |
| 数据库 + 全量用户数据 | ✅ | 订单 99.84% + 评价 100% + 卖家 100% |
| 接管后台 | ❌ | 口令强 bcrypt；Cloudflare 全面挑战；过滤器鉴权正确 |

**要点：数据面通了不等于权限面通了，报告里必须把三目标分开写死，别用"拿下"一词糊过去。**

## 唯一剩余链（组件已验证，未实战）

```
未授权上传 SVG（已确认）
  → 载荷托管 shop/images/xxx.svg（同源执行）
  → shop 与 seller 共用同一 newlogin token（localStorage.token）
  → 诱导访问 SVG → JS 读 token 外带
  → 拿 token 打 /api/user!LoginFree.action
```

这条链的启示：**同一套后端给多个子域发 token 时，任一子域的存储型 XSS 等于全站接管**，SVG 上传是最常见的入口。

## 边界 / 坑

- 后台 bcrypt + CF 挑战，硬爆无意义
- 别把"未授权上传 SVG"当 RCE 报——它是 XSS/ATO 的前置，不是代码执行
- 全量遍历要控速，`pageSize=50` 打 1055 页已是万级请求，别一次全开

## 检查清单

- [ ] 找 `*.action!method` 路由，逐个方法测鉴权（`!list` / `!info` / `!update`）
- [ ] 对每个接口做 `type` / `view` / `flag` / `isAdmin` 参数差分，看返回字段变化
- [ ] 用列表接口的 `pageNum` 探总数上限，评估遍历成本
- [ ] 找关联键（`partyId` / `userId` / `orderId`）把多表缝成画像
- [ ] 合同/发票类 URL 单独归档
- [ ] 三目标（RCE / 数据 / 后台）分别给结论，不合并
