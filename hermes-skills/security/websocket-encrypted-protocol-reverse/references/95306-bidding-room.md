# 95306 竞价室实录(2026-08-31 实证)

## WS 连接模板(已破解)

```
wss://cg.95306.cn/business/msg/websocket/<enc1>/<type>/<enc2>
enc(x) = base64(SM4-ECB(key, x)).replace("/", "jingjia")
key = (YYYYMMDD + "$e9s20@2o4u^r2")[:16]   # 每日动态,北京时区;与 HTTP bidding 网关同款 key
type: 00=竞价室(offer) / 01=监视(monitorOffer) / 02=监控(surveilOffer)
enc1 = enc(组件依赖值 c["a"]()), enc2 = enc(radio=packId)
```

- 消息:`JSON.parse(sm4decryptEcb(key, e.data))`;msgType: heartbeat/offer/monitorOffer/surveilOffer
- 出价推送含包件状态 + 出价企业(offer = 实时出价数据)
- 竞价室页面 chunk:chunk-0cb9a2b8(01)/4c23e66b(02)/4df22b34(00);websocketAddress 在 chunk data 区

## 通道边界(核心结论)

- **审计日志只记 bfwz 网关(报名/查询/公告跳转);竞价室(business-bidding 网关 + WS)操作 0 审计记录**(审计里 business-bidding/bidRoom 关键词 0 条,竞价日 23 家报名企业 0 条操作)
- 报名期 = 审计拦截有效(redirectEnrollUrl 带 serviceTicket);竞价期 = 审计失效
- WS 连接需要"报过该包件的企业 ST"——无权限账号握手 101 后立即 0x03e8 关闭
- **数据获取策略**:报名期拦截(getSupplierPackageList buyed → 每项目 getBuyPackageList);竞价期只能等竞价结束兜底(`aggregation_bfwz_bfwzpackage_a` 已结束包件表,含 pack_id);竞价中唯一路径 = 拿到报名企业 ST 连 WS

## SM4 密钥材料

```
b = "$e9s20@2o4u^r2"; p = "memberserver"
key_y = (日期 + b)[:16]   # 加密/WS 用
key_g = (日期 + "+" + p)[:16]  # memServer 用
```

纯 Python SM4-ECB 过国标向量:key=pt=0123456789abcdeffedcba9876543210 → ct=681edf34d206965e86b3e94f536e4246。

## 未验证项

- bidRoom HTTP(packTable/initProjInfo)响应密文在所有 key 变体下解不开 → 怀疑同样要求"报名企业 ST"(拿到业务 ST 后优先重验)
- 竞价结束兜底补全链路待竞价结束后验证(西安局69次 15:34 结束)

## 相关技能

- `webapp-api-crypto-reverse` — 同站 HTTP 加密 API 逆向方法论(SM4 key 推导、webpack chunk 提取)
- `monitoring-pipeline-ops` — 采集机/merger 管道运维(审计拦截、分片、企业全量比对)
- `auditlog-ticket-harvesting` — 审计活票收割(报名期 ST 来源)
