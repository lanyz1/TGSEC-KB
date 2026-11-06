# 源站定位与裸端口面(若依-Vue-Plus 实战实测)

## 1. 从 CF/WAF 后面把源站挖出来

两把最有效的测绘招(实测一次命中,且互相补盲区):

```bash
# ① 证书 CN 直指后台域名 → 源站 IP
shodan search 'ssl:"taskking.shop"'          # → 103.59.145.84,证书 CN = admin.taskking.shop
# ② 用后台标题在全世界找同源码实例 → 顺带发现第二套生产环境
shodan search 'http.title:"126310后台管理"'   # → 217.194.133.198(独立库、独立后台账号)
```

要点:

- **标题命中、域名不同号的第二个 IP = 另一套生产环境**(独立库、独立后台账号),别当镜像忽略;两套环境的用户/资金口径都要各自核
- CF 只代理 http/https 标准端口;**源站 IP 一旦暴露,3306 / 18080 / 19000 / 19001 / 888 全部直达**
- 域名被摘(注册局委派撤销 / 公共 DNS NXDOMAIN,被查封盘口常见)时,`dig` 全空 **≠ 站点关了**,直接走 IP + Host 头或 `curl --resolve`:

```bash
curl -sk --resolve admin.target.shop:443:<源站IP> https://admin.target.shop/prod-api/getInfo
```

## 2. 裸端口矩阵(命中后逐个定性)

| 端口 | 是什么 | 怎么用 |
|---|---|---|
| 18080 | **Spring Boot 裸端口** | **绕过 nginx 直通**:`/v3/api-docs`、`/actuator/health`、`/system/config/front/*` 不过 nginx 上的过滤与限流 |
| 19000 / 19001 | MinIO S3 API / Console | SigV4 直连列桶;控制台(:19001)常也对外 |
| 3306 | MySQL | 弱口令 → 全库;先判 `SHOW GRANTS` / `@@secure_file_priv` |
| 3000 | 静态站(同盘另一个业务面) | 常是引流落地页/静态资源,是"业务模式定性"的素材 |
| 887 / 888 | 宝塔 phpMyAdmin | 通常按 IP 白名单拒绝;判据与绕过清单见 `04-negative-verdicts-and-redlines.md` |
| 5432 | PostgreSQL | `pg_hba` 常拒外部来源 → 死路,记录即可 |

## 3. 扫描纪律(踩坑记录)

- **对生产源站不要全端口高并发**:600 并发跑完 65535 端口 → 目标防火墙按出口 IP **整机封禁**(当时源站 A 对我方彻底不可达;CF 回源仍正常、真实用户无感)。
- 正确做法:白名单端口(上表)+ 低频 + 从跳板出口;被封后先确认"业务与用户是否受影响"(经 CF 请求业务接口仍 200 = 只伤自己通道),再决定是否换出口。
- 只做**指纹级**探测:拿到 banner / 证书 / 标题就够,不做服务层爆破。
