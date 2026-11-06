# FastAPI/Python 后端 RCE 攻击面优先级(惊蛰量化实战)

2026-08-12 惊蛰量化(app.jing-zhe.com, Python FastAPI + nginx, 新加坡 AWS) RCE 攻坚阶段 2。FastAPI 后端与 PHP 完全不同: LFI/PHAR/上传 webshell 系全不适用, 主攻执行引擎与代码字段。

## 攻击面优先级(实测排序)

```
1. 管理端执行引擎 (backtest/run)     ← 最强: 真的执行代码/拉数据
2. 指标/模板代码字段 (indicator-definitions) ← 可存任意 code, 待确认回测时是否 eval
3. 爬虫/同步接口 (news/crawl, partners/sync) ← 白名单, 已排除
4. 用户端编译器 (pine/compile)       ← 真入口但需 user token
```

## 管理端执行引擎探测法

**入口**: 管理前端 JS chunks 提取 API(不是 openapi.json, admin 接口只在 JS):
```bash
cat chunks/*.js manage_*.js | grep -oE '"/api/admin/[a-zA-Z0-9_/{}$.-]+"' | sort -u
```
关键词过滤找执行面: exec/run/task/compile/import/upload/crawl/test/callback/backtest/simulate/execute/shell/command/deploy/eval/code/script/strategy

**"执行引擎活"的判断标准**(关键):
- 错误从"参数校验"(422/Field required/请选择官方策略)→ 变成"业务执行错误"(如 `WEEX 合约K线不支持周期: 1h` / `K线有效价格数据不足`)= 已进入执行链
- 之前所有 exchange 注入测试返回 `status=failed` 是因为没传 `official_strategy_id`(必须 `backtest_source:"official"` + `official_strategy_id` 如 407)

**backtest/run 最小可用 body**(从 chunks/index.8bb2055c.js 提取):
```json
{"strategy_name":"x","strategy_desc":"x","strategy_tag":"x","strategy_category":"精选策略",
 "strategy_type":"official","backtest_source":"official","official_strategy_id":407,
 "exchange":"WEEX","symbol":"BTC","timeframe":"5m","leverage":10,"init_cash":10000,
 "backtest_mode":"bar","params":{"official_strategy_id":407},"start_date":"2026-06-01","end_date":"2026-08-01"}
```

## indicator-definitions 代码字段

- `POST /api/admin/entry-filters/indicator-definitions/` 可创建任意 `code` 字段, **后端不校验**(`__import__('os').system('id')` 都创建成功)
- code 字段在用户端回测时如何被执行 = 潜在 eval RCE, 待验证
- 类似字段: filter-templates items[].indicator_code、strategy-templates

## 已排除面(别重测)

| 接口 | 排除原因 |
|---|---|
| `POST /api/admin/news/crawl` | source 参数被白名单覆盖(odaily/chaincatcher/blockbeats/coindesk/bankless/thedefiant),传 URL 无变化 |
| `POST /api/admin/partners/sync-weex` | host 参数被忽略,走默认配置 |
| `GET /api/admin/partners/sync-config` | 泄露内部域名 `affiliates.wjekenx.online`(CloudFront 54.230.201.94, WEEX affiliate 系统)= 兄弟资产 |

## 用户 token 获取难点

- 注册: verification_code 必填, send-verification-code 不回显验证码
- 测试号 <EMAIL-REDACTED> 常见密码全错(用户名或密码错误)
- admin 端无用户密码重置接口(admins 是管理员不是用户)
- 下一步可试: 验证码爆破(4位)/ 邮件 token 不可爆(记忆已有)/ 换交易所跑通 backtest 基线

## 其他

- WEEX K线只支持 1m/5m/15m(4h/1d 报"不支持周期"), 但 5m 报"K线有效价格数据不足"(2026-01~08 全试过)→ 卡在数据源, 可试 Binance/OKX/Bybit 或确认 K 线数据接口
- 环境: token 在 `D:\渗透\jingzhe_apk_recon\admin_token.txt`(有效), user token 已过期
