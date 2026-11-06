# 实战回放:taskking.shop(ENG-20260924-02)「126310后台管理」+ 风暴扑克 + FB 刷单盘

## 1. 定性

RuoYi-Vue-Plus 4.8.2 + 自研 `com.ruoyi.facebook.*` 模块;真钱扑克(风暴扑克·好友房) + Facebook cloaking 落地页引流刷单盘。**两套独立生产环境**(.84 / .198)。从默认口令到云 Root 密钥全链 < 1 天。

## 2. 攻击链(10 步)

```
[1] admin/admin123 + 验证码随便填 → 后台超管 permissions:["*:*:*"]        ← 9.8
[2] 后台全局接口 → 全量业务数据(用户/银行卡/USDT/明文交易密码/KYC/资金)
[3] 未授权 OpenAPI 328 路径 → 未授权 KYC oracle(fb_id = 毫秒时间戳)
[4] front/{key} 配置路由绕过 → 更多密钥
[5] monitor/cache 读 Redis 全命名空间 → 14 个在线会话令牌 + 全部密钥明文
[6] Shodan(ssl: / http.title:) 定位源站 → 3306 facebook/facebook → 61/53 表全库
[7] 源站 19000 MinIO + sys_oss_config 凭据 → 对象桶全量读写(SigV4 200)
[8] /oss/ 反代内网 MinIO 且桶无策略 → KYC 证件照公网直下(200 image/png)
[9] 任意 .html 上传 → 平台引流域名下托管任意内容
[10] sys_config 的 tencent.translate.* → 腾讯云 **Root** 密钥(真实可用)
```

## 3. 关键证据(可复用为判据)

- **登录**:`POST /prod-api/login {"username":"admin","password":"admin123","code":"9999"}` → 200;`getInfo` 返回 `roles:["admin"]`、`userId=1`
- **KYC oracle**:`GET /prod-api/facebook/userVerify/getInfoByFbId?fbid=<17位>` 匿名 200(realName / idCard / 证件照 OSS 地址 / email / phone);
  `POST .../userVerify/submit` 空 body → `{"code":200,"msg":"<base64>"}`,解码 `{"fb_id":"20260925002803979","lang":"en"}` ⇒ **fb_id = 服务端毫秒时间戳,可无限铸造**;匹配语义 = 17 位精确匹配(截断/邻值 → 500)
- **身份来自客户端**:`getUserInfo` 用 **X-Forwarded-For** 当身份标识(`XFF: 1.1.1.1` → `fbNickname:"1.1.1.1"`)⇒ 风控/限流来源可伪造
- **会话面**:`/monitor/online/list` = 12 个在线会话,来源 IP 覆盖老挝/伊朗/中国成都/AWS HK(现成的运营位置情报)
- **前端认证设计**:`config.headers['Fb-Id'] = localStorage.getItem('fbId')`,服务端**无签名绑定** → 一个头就是身份索引
- **第二后端指纹**:`/facebook/user/crash_log` 信封与主站不同,且**反射任意 Origin(含 `null`)+ `access-control-allow-credentials: true`**,响应头 `server: cloudflare` ⇒ 疑为边缘 Worker 实现,鉴权边界另算
- **生产残留**:后台仍有作者 demo 账号 `lionli`、`test_demo` / `test_tree` 表、demo 控制器启用

## 4. 数据面(两环境对照)

| 指标 | .84(taskking) | .198(adsm12360) |
|---|---|---|
| 用户 / KYC | 75 / 139 | 288 / 251 |
| 提现申请 | 55 | 309 |
| 充值 | 492 | 669 |
| 操作 + 登录日志 | — | 37,738 行(53 表) |
| 对象 | 1,166 | 2,127 |

## 5. 业务定性(刷单/杀猪盘)

- **无任何支付网关**:充值 `recharge_type` 100% = `0 系统充值`、`screenshot` 全空、`create_by` 是运营账号且 `create_time == update_time` ⇒ **全线下入金 + 后台人工上账**
- **出金全手工**:银行卡/ETH 两类,`update_by` = huangjin / mingwei / shiliu888,**不接任何银行或支付网关的自动出款接口** ⇒ 驳回权 100% 在运营手里
- **话术**(日文,48+ 笔带理由):「2888万円のキャンペーンがまだ完了していない」「**違約金をお支払いいただいた後、全額出金することが可能です**」= 缴纳违约金话术;另有"广告未投放/信用分未达100/卡号与户名不符"
- **系统内置 `is_trial_account` 试玩号**:.198 有 210/288(73%)标记为试玩号,其成功放款占全站 94.5% ⇒ **对外展示的"能出金"大多是自己开的号**(`江南试玩账户`/`龙五测试号`)
- 真实回款率公式与口径 → `wallet-exchange-fund-verification/references/ponzi-crosscheck.md`

## 6. 未取得 OS 层 RCE —— 诚实结论

6 条 RCE 级原语全部实测:云 Root 密钥(无 CVM,LightHouse 无 `RunCommand`)、MinIO 管理面、全库 DML(无 FILE)、上传 + 公开域(仅 web 内容)、代码生成器(**模块不可用**)、OSS 配置 SSRF(**触碰稳定性红线**) → 依次被「无文件写权限 / 生态组件缺失 / 稳定性红线」挡住,**未落地 OS 命令执行**。报告里要逐条写清卡点判据,而不是含糊写"未 getshell"。
