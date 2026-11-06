---
name: oss-default-credential-takeover
description: "开源产品上生产未改默认凭据/默认密钥时: 种子号+自签令牌接管。"
---

# 开源产品默认凭据接管

适用：WiseMapping / GMPay(epusdt) / Chatwoot / SnappyMail / ShopXO 这类自托管开源产品被直接部署上生产。核心不是爆破，是**源码里的默认值还在不在**。

## 流程

1. **定版本** — 页面/接口/JS 拿精确版本或 tag，clone 对应源码。版本不对，默认值表就错。
2. **掘默认值** — 按产出率排序：
   - `data-*.sql` / `*seed*.sql` / migration 里的**种子账号**（`test@...`、`admin@...` + SHA1/MD5 口令）
   - `application.yml` / `application.properties` / `.env.example` / `docker-compose.yml` 里的 **JWT/加密密钥**
   - 安装器默认管理员（`/install`、`auth/init-password` 返回的初始口令哈希）
3. **试种子账号** — 直接登录。注册开的站要注意：邮件服务挂了会导致账号建成但未激活，激活码常是 UUID 低 64 位（**不可爆**，别再花轮次）。
4. **验默认密钥** — 拿一个**真实 token**（种子号登录所得），用**同版本库**离线验签：
   ```bash
   # 下载 jjwt-api/impl/jackson 与 jackson-databind 到本地，写 20 行 Java 验签
   javac -cp 'jwtlib/*' T.java && java -cp 'jwtlib/*:.' T <token>
   ```
   ⚠️ **jjwt 的坑**：`Decoders.BASE64.decode()` 把非法字符（如密钥中间的 `=`）当零值六位组，等价于 `A`。Python `base64.b64decode` 会报错/截断，导致误判「密钥不对」。
   实测：`SECRET.replace("=","A")` 解出 57 字节 → HS384 验签通过。
5. **自签管理员** — 从配置取管理员标识（如 `app.admin.user=admin@...`），签 `sub=<该标识>`，调**仅管理员**接口。
6. **闭环判据** — 必须拿到 `isAdmin:true` 或真实业务数据；SPA 兜底页的 200 不算（Actuator 要用 JSON 端点复核，别被 HTML 假 200 骗）。

## 接管后先做现实核查

开源实例常是**空壳**：只有前人渗透测试留下的测试号、默认模板图。拿到超管不等于拿到数据 —— 先列用户/内容，再决定值不值得继续。报告写「已接管，实例无运营数据」，不要写成数据泄露。

## 常见默认值位置速查

| 产品 | 默认点 |
|---|---|
| WiseMapping | `data-postgresql.sql` 种子号；`application.yml` 的 jwt secret（HS384，含 `=`） |
| epusdt/GMPay | `auth/init-password` 吐初始口令哈希；商户密钥在库/配置 |
| Chatwoot | `admin@example.com` / 安装时设的密码；`ENABLE_ACCOUNT_SIGNUP` |
| SnappyMail | `/?admin` 默认 `admin/12345`；`_data_/_default_/admin_password.txt` |
| ShopXO | `/install.php` 默认管理员；后台随机路径 |

## 关联

`jwt-attacks`（算法/claim 面）、`admin-credential-hunt`（非默认口令场景）、`snappy-*` 类面板卡。
