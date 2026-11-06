# 会话 token 直接复用:从库/备份表取后台会话 + "已修复"逐入口复测纪律

来源:2026-09 灰豚/央选族(自研 Yii2 后台 `desktop.sviptrader.com`)。

## 1. 机制:会话 token 当普通列存在用户表里

很多自研后台**不做 session 表**,直接把"已登录"当成用户表的一个 `token` 列:

```php
// controllers/ParentController.php
if (isset($_COOKIE['token']) && strlen($_COOKIE['token']) == 32) {
    $user = AdminUser::find()->where(['token' => $_COOKIE['token']])->one();   // 命中即已登录
}
```

**没有 TTL、没有 IP/设备绑定、不改密失效、无服务端吊销** —— 于是:

> **能读到这张表的任何途径 = 后台会话清单**。不需要口令、不需要爆破、不需要伪造签名。
> 途径:云备份桶(DBS/导出 Parquet)、只读库账号、SQLi、导出接口、heapdump、`.sql` 备份包。

判据(读源码,30 秒):搜 `$_COOKIE['token']` / `cookies.get('token')` / `getUserInfoByToken`,
看是否只比长度 + 查表,**没有任何时间/设备/参数校验**。是 → 全部 token 即插即用。

## 2. 复测纪律:"已修复"必须在被点名的每一发上分别验证

2026-09-21 实测(距首轮 5 天),同一份报告里列出的四条路径,修复状态**完全不一致**:

| 入口 | 5 天前 | 复测 | 判定 |
|---|---|---|---|
| 老免鉴权 STS `oss-sign` | 200 出 STS | `401` | ✅ 已修 |
| 免密 `pre-login`(只发 username) | 无凭据返回 preAuthSign | `422 密码不能为空` | ✅ 已修 |
| **零鉴权 STS `micro-cyt/oss/sts`** | 200 出 STS | **200 仍出 STS** | ❌ 未修 |
| **admin 会话 token(13 个)** | 未测 | **13/13 仍 302 已登录** | ❌ 未修 |

结论模板:**对方通常只堵"报告里公开点名的那一发",同一漏洞的兄弟入口/同类会话机制不动。**
所以复测要按**入口**逐个做,不要按"漏洞"整体下"已修/未修"的判断,更不可因一发 401 就写"已修复"。

三类响应的判据各不相同:
- **会话/token**:看 `302`(已登录,跳走)vs `200`(回登录页) —— 不能只看接口 HTTP 200
- **业务 API**:看业务 `code`(401 vs code:0),不看 HTTP 码
- **云 STS**:看能否兑出凭证(`AccessKeyId` 出现即未修)

## 3. 拿到会话后怎么取证(避免"页面进去了≠打进去")

1. `GET /index/index/` → 200 + title + 字节数
2. **从首页 HTML 里抠出全部菜单路由**(`href=`/`data-url=`/`lay-href=`),这才是真实路由表:
   ```python
   re.findall(r'(?:href|data-url|lay-href)\s*=\s*"([^"]{4,90})"', html)
   ```
3. 逐个 GET 关键数据页(列表/统计/角色/管理员管理),**页面字节数 + title 作 PoV**;
   `/statistics/pool-data/` 这种业务视图页动辄 278 KB = 硬证据。
4. **写操作面(改渠道/改价/加成本商品/黑白名单)只记录"菜单存在 + 可访问",不调用** ——
   业务影响不可逆,写进报告"可写面已具备,未实施"。
5. 路由陷阱:应用根就是 `/`,路由形如 `/index/index/`、`/merchant/list/`。
   别自作聪明加 `/admin` 前缀(`/admin/index/index/` → 18 字节 `页面未找到。`),
   也别漏末尾斜杠。**一律用从首页抠出来的原样路径回打**,不要手拼。

## 4. 备份库里的弱口令账号 ≠ 现网账号

同一张备份表里的"弱口令命中"可能属于**已停运的 legacy 库**:
- 口令哈希(无盐 md5)确实能反查出明文(命中率 7%~14%),**但账号在现网平台不存在**
- 探针:`pre-login{username:<手机号>}` → `1002000011 手机号暂未注册账号,请先注册`
- 旁证:该表用户的 `last_access_time` / 第三方 token 过期时间集中在 **2021–2023**

**先发一发注册态探针定归属,再决定要不要声称"N 个账号可登录"**,否则交出去的是假战果。

## 5. 客户端签名盐硬编码 → 任意人可离线复算

同一族客户端(Electron/H5)把盐写死在 bundle 里:

```js
f = "123456"                                        // 签名盐
sg = md5( join(sorted(k+v for k,v in params+body)) + f )
params = {ct:"pc", ts:<unix秒>, si:<md5(di+ms)[:4]+[-4:]>, di:<设备号>, nt:"wifi", vn:"1.0", im:""}
```

用 Python 复算即可驱动全部 API(实测 6 个脚本全部通过校验):
```python
def sg(q, d, SEC="123456"):
    o = dict(q); o.update(d or {})
    return hashlib.md5(("".join("%s%s" % (k, o[k]) for k in sorted(o)) + SEC).encode()).hexdigest()
```
**字段名靠报错反推**:`{"loginName":..}` → `422 登录账号不能为空`;`{"username":..}` → 推进到
`密码不能为空`/`手机号暂未注册账号`。一次只换一个字段名,7 个以内必中。
