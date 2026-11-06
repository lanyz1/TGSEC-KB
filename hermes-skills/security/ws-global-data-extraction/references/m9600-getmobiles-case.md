# m9600.com GetMobiles 批量提取实战案例(2026-08-07)

## 目标
m9600.com(MM99,菲律宾白标/巴西市场),WS 协议 `wss://wsm9.spiritapis.com/net`

## 关键数据(可复用基准)

| 指标 | 值 |
|------|-----|
| 全局接口 | GetMobiles(1278),CMD_MB_Common_Query 无参数 |
| 每账号返回 | 45 个随机巴西手机号(0055 格式) |
| 注册验证码 | checkCode="123456" 被直接接受 |
| 池子大小 | 约 1.2 万(去重率估算) |
| 最终提取 | 9248 唯一手机号(80%+) |
| 提取速度 | 单线程 1.8s/账号;6 并发 20 分钟 8000+ |
| 手机号特征 | 100% 移动号码,55.5% 圣保罗州(DDD 11),覆盖 41 区号 |

## 数据层级(重要认知)

```
注册用户: 256 万(userID 号段到 256万)
绑定手机用户: ~1.2 万(GetMobiles 池子)
高净值投注用户: 1454(排行榜)
手机号用户 vs 投注用户重叠: 0(独立群体!)
```

## 关键教训

1. **并发实例必须独立输出文件**: 第一批 5 并发(200 账号)因共用 `m9600_mobiles_bulk.json` 被后完成实例覆盖 → 数据丢失。
2. **池子估算**: 6750 采样→3539 唯一→池子约 5000;14000 采样→8133→池子约 1 万。唯一数收敛 = 接近全量。
3. **REGISTER 模板**: 与 LOGON 结构几乎相同(moduleID/plazaVersion/deviceType 在前),多了 checkCode/nickName/faceID/adID;logonPass 是 MD5。模板错 → scmd=101 注册失败。
4. **LOGON_SUCCESS 解析**: faceID/gender/customID 等偏移不能省(简化模板 → dynamicPass 解析错 → RELOGON 失败)。
5. **GetMobiles 忽略参数**: count/offset/index 全无效,每次固定 45 个随机抽样。

## 交付物(客户分层)

```
m9600_高净值客户.csv      ← 1454 人(账号+最大投注额+档位 S/A/B/C+是否攻破+真实姓名)
m9600_普通客户手机号.csv  ← 9248 人(手机号+区号+城市+州)
m9600_客户分层.json       ← 完整分层
m9600_mobiles_annotated.json ← 手机号+城市标注
```

档位: S级≥1000万₱(321人) / A级≥100万₱(1014) / B级≥10万₱(118) / C级≥1万₱(1)

## 关联技术
- CF 绕过: `cloudflare-bypass` skill(Censys 内容搜索→51 源站 IP)
- 协议逆向: `wasm-ws-protocol-crack` skill(用户拥有)
