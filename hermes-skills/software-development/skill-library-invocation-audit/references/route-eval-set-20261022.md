# 现场口语评测集（2026-10-22 基线）

16 条「渗透现场会说的话」，用于回归路由精度。跑法：

```bash
python3 scripts/route_eval.py /tmp/eval.json --phase recon   # auth / injection 各跑一遍
```

基线：修前 TOP1 6/16 · TOP3 10/16 · MISS 3/16 → 补完元数据后 TOP1 15/16 · TOP3 16/16 · MISS 0/16（三个 phase 一致）。
唯一长期非 TOP1 的是「宝塔 面板 密码 忘了」（rank 2，rank 1 是同族 `self-hosted-panel-takeover`，家族判定仍正确）。

```json
[
 {"q": "NginxWebUI 默认密码", "expect": ["self-hosted-panel-takeover"]},
 {"q": "盲注 没回显 怎么判真假", "expect": ["sqli-manual", "sqli-sql-injection"]},
 {"q": "SSH 走 socks5 代理 单跳", "expect": ["network-tunneling", "internal-tunnel"]},
 {"q": "Druid 监控台 登录 口令", "expect": ["springboot-druid-jwt-aws-killchain", "ruoyi-fork-admin-pentest"]},
 {"q": "PHP 大马 藏哪 不被扫", "expect": ["webshell-stealth-persistence"]},
 {"q": "iOS 水坑 按版本 分发载荷", "expect": ["darksword-coruna-c2-pentest"]},
 {"q": "宝塔 面板 密码 忘了", "expect": ["bt-panel-pentest", "admin-credential-hunt"]},
 {"q": "TG 号库 session 导入", "expect": ["tg-account-library"]},
 {"q": "对象存储 匿名 可读 桶", "expect": ["anonymous-object-storage-access"]},
 {"q": "422 判断 未授权 管理接口", "expect": ["unauthenticated-admin-api"]},
 {"q": "若依 定时任务 白名单 RCE", "expect": ["ruoyi-quartz-whitelist-bypass-el-rce"]},
 {"q": "注册 参数 多传 变管理员", "expect": ["mass-assignment"]},
 {"q": "nginx off-by-slash 路径穿越", "expect": ["nginx-misconfig"]},
 {"q": "heapdump 里 找 数据库密码", "expect": ["heapdump-lanniao-hunter"]},
 {"q": "卡商 后台 进不去", "expect": ["card-merchant-platform-pentest"]},
 {"q": "1z 白标 盘口 签名", "expect": ["1z-gambling-family-pentest"]}
]
```

## 扩展集（2026-10-22，96 条，`arsenal/eval_core.json`）

16 条基线只够防退化，不够证明“换说法还调得到”。已扩到 96 条：

- 84 条覆盖 recon / auth / injection / file / ad / cloud / mobile / cms / api / gambling / ai / reverse / tools / report，**neutral（`--phase none`，不带阶段先验）**；
- 12 条同义改写（同意图换说法）：宝塔“忘记密码进不去”、sqlmap“跑不出结果”、桶“能列目录吗”、heapdump“怎么翻密码”、上传“传个 php 马”等。

首跑 **TOP1 47/84 · TOP3 59/84 · MISS 25/84**，根因两类：expect 写错（`captcha`、`container-security-testing` 本来就是最佳卡）、元数据缺现场说法（英文卡没有中文触发词）。补完：**TOP1 93/96 · TOP3 96/96 · MISS 0**（含 12 条改写）。

维护规则：新增 case 时 **expect 要包含“确实更合适的 rank1 卡”**，否则会把正确路由误判成 miss；但也不能见 rank1 就收——`campaign-router` 抢 `kerberoasting` 这种属于真缺陷，得补词而不是改 expect。

## 设计要点

- **用现场说法，不用卡片名**：拿卡片名去测会全绿，等于没测。
- **每个 expect 带同族候选**：只认单一卡名会把「正确家族但排第二」误判为失败（如 sqli 家族）。
- **必须含同族对照对**：`宝塔` vs `自建面板`、`sqli` vs `ldap`、`S3` vs `对象存储`——补词抢位只有对照对才看得出来。
- **新增 TTP 就加一条**：这批吸收的每条新打法，都应该在评测集里有一条「现场会怎么问」的记录，否则下次没人知道它调不调得到。
- **别为了 TOP1 动全局权重**：网格实测（6 组）证明卡名前缀加权/headings 封顶/路由卡衰减全是负收益，回滚后默认参数最优。精度问题用定向补词解决。
