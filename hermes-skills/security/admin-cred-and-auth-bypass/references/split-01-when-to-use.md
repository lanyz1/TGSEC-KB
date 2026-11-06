## When to Use

触发: 遇到 admin / 管理端 / 运营后台 / 管理面板 / dashboard 登录页,而**账号密码未知**;
正在跑弱口令或大字典**打了好几个小时没进**;被要求"打进管理后台"。

配套(按需接力):
| 已有 | 去哪 |
|---|---|
| 管理端域名都找不到 | `admin-console-discovery`(通配证书 CT 反查 + vhost 枚举) |
| 拿到凭据要脱库 | `lowcode-admin-data-exfil` / `userdata-grab` |
| 进后台要留后门 | `admin-backdoor-persistence` |
| 拿到 JDBC/Shiro 密钥 | `java-framework-deserialization-family` / `middleware-unauth-family` |
| 卡密/发卡类后台 | `card-shop-pentest` / `open-source-faka-pentest` |

---

