# 厂商公开仓库 / 镜像里的生产凭据（含口令派生反推）

## 0. 前提认知

做白标/发卡/账号工厂这类生意的，代码和镜像**由外部厂商提供**（"翎云"类技术团队）。厂商自己会：
- 把内部框架半开源到 GitHub（`<vendor-org>/<Product>`）；
- 把**生产配置文件**提交进公开仓库（没进 `.gitignore`）；
- 给多个客户站点复用同一套默认密钥与默认口令。

⇒ **一把凭据 = 一条产品线的入口**。这是"打不动单个客户站"时的正解。

## 1. 先定位厂商 org（线索按命中率排序）

- Harbor 镜像名与 annotations：`library/<product>:nightly` → 产品名；
- Gitea 组织名与仓库路径（`<org>/<product>`）、仓库里 `docker-compose.yml` 的镜向前缀；
- 前端注释 / 页脚 / `package.json` 的 author / 证书 O / 客服联系方式；
- ★ 镜像内 `vendor/*/.git/config` 的 `remote.origin.url` —— 直接吐 GitHub/GitLab 组织名与 namespace 结构；
- 页脚/关于页的"技术支持"字样 + 拼音缩写（如 `tools92`、`nsnail`）。

```bash
curl -sk "https://api.github.com/orgs/<org>/repos?per_page=100&sort=updated"
curl -sk "https://api.github.com/users/<user>/repos?per_page=100"
curl -sk "https://api.github.com/repos/<org>/<repo>/branches"       # main / master / dev 哪个默认
curl -sk "https://api.github.com/repos/<org>/<repo>/contents/"      # 列目录，不必 clone
```
> 别用 GitHub `search/code`（要登录、有配额、还常搜不到私有组织）。**先拿 org 名，再列 repos/contents。**

## 2. 直读文件（不 clone，省足迹与时间）

```bash
# 单文件：raw 直读，最快、无 API 配额
curl -s "https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path>"
# 批量：浅 clone
git clone --depth 1 https://github.com/<org>/<repo>.git
```

**必查文件清单**（.NET / Java / Node / PHP 通用）：
```
appsettings.json  appsettings.Development.json  appsettings.Test.json
appsettings.Remote.json  appsettings.Production.json
application.yml  application-dev.yml  application-prod.yml  bootstrap.yml
.env  .env.prod  docker-compose.yml  docker-compose.*.yml
k8s/*.yaml  helm/values.yaml  .gitlab-ci.yml  Jenkinsfile  deploy.sh
*.pubxml  web.config  AdmSettings.json  NetAdminSettings.json  SeedData/Sys_User.json
```

⚠️ **重点找 Remote / Test / Prod 这类带环境后缀的文件**：`Local.example.json` 里是占位符（示范正确做法），
而 `Remote` / `Test` 里往往塞的是**真连接串**（厂商内部开发把 "Remote/Test" 当"我自己连的库"）。

**优先级判断**：同一 org 里优先看
① 名字像框架/模板的仓库（`<Product>.Api` / `AdmServer` / `Template`）；
② 带 `Remote`/`Test`/`Prod` 配置的仓库；
③ CI/deploy 仓库（里面有生产 host/IP）。

## 3. 拿到凭据后的验证顺序（只读优先）

| 凭据 | 只读验证 | 备注 |
|---|---|---|
| MSSQL / MySQL 连接串 | `SELECT 1` / 列出库名 | 内网地址（`172.16.` / 专有网段）常 filtered：先在**公网可达**资产上试复用 |
| Elasticsearch `elastic:<pw>` | `GET /_cluster/health` | 成功即转 `logstore-dump.md` |
| MinIO AK/SK | 列桶 | 别先下大对象 |
| JWT `IssuerSigningKey` | 本地自签 token 打一个只读接口 | **无痕，首选** |
| Redis | `PING` / `INFO` | 平台里常存 session / captcha |
| Captcha `SecretKey` | 本地生成验证码走只读校验接口 | 见 `netadmin-furion-stack.md` |

## 4. ★ 口令派生反推（把哈希变明文）

框架常有**确定性派生**（无盐、无随机迭代）：

```
Pwd(pw) = HMAC-MD5(key = MD5_hex(pw), msg = pw)   → 32 位 hex
```

```python
import hashlib, hmac
def pwd(pw: str) -> str:
    return hmac.new(hashlib.md5(pw.encode()).hexdigest().encode(),
                    pw.encode(), hashlib.md5).hexdigest()
# 用 SeedData 里的 hash 反查
for w in open('dict.txt', encoding='utf-8').read().split():
    if pwd(w) == target_hash:
        print('HIT', w); break
```

- 字典**不需要大**：团队默认口令 / 公司名+年份 / `admin@123` 这类几百~几万条足够。
- 确定性 ⇒ 一次命中可跨员工、跨服务复用（这就是"团队默认口令复用"的来源）。
- 反推结果**只做只读验证**（登 Gitea/ES 的只读面），**不改口令**。
- 派生算法来源：反编译镜像里的程序集（有 `.pdb` 更轻松）、框架源码仓库的 `*Service.cs`。

## 5. 反模式

- 只搜 code search、不列 org repos（配额耗尽且漏）。
- 拿到连接串就冲内网库（多半 filtered，白耗）—— 先验**公网可达**的服务。
- 把"仓库里有凭据"直接写成"已接管" —— 必须**只读验证成功**才能下结论。
- 在客户站点验证厂商默认值失败后就放弃整条线 —— 应改为**拿默认值去搜同栈其它站点**（见 `netadmin-furion-stack.md` §5）。
