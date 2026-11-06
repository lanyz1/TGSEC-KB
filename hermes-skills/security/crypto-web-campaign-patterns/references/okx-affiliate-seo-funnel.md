# OKX 拉新 SEO 静态壳漏斗（ACE53 渠道）

## 定性

Cloudflare/nginx **纯静态**假 Web3/交易所/钱包下载站 → 跳板域 atob 混淆 → **仿 OKX join** + **大体积 APK**。  
入口 **无后台可打**；价值在渠道号、同源基建、APK 反编译。

**不是** 授权盗 U、不是 MT5 门户、不是 Destoon 发卡。

---

## 指纹

| 信号 | 例 |
|------|-----|
| 落地标题 | Web3 质押挖矿 / ave.ai 下载 / Topay 钱包 / 假 OKX |
| 按钮 | `reg.oereg.com` / `reg.ouyir.com` 的 appd.html / webs.html |
| 跳板 | `www.toprvkxwhpm.com`、`www.mxkdpwvhqrn.org`（EdgeOne eo.dnse4） |
| atob reverse | `atob(str.split('').reverse().join(''))` → `cbjollery.mpwrs.cn` / `btmzhjpdgxc.org` |
| 渠道 | `channelId=ACE53xxxx`（如 530992 / 531246 / 531722） |
| join | `https://www.btmzhjpdgxc.org/zh-hans/join?channelId=ACE...` 资源 `static.coinall.ltd` |
| APK | `https://cbjollery.mpwrs.cn/upgradeapp/android_ACE....apk` ~450MB+，包名常 `com.okinc.okex.gp` 真 OKX 壳 |
| 站群 | 随机子域 SEO 页（roslyn1.com 系）；admin/api 子域 302 回主站 |

### 案例入口（2026-09）

- `skhe.roslyn1.com` / `roslyn1.com` → reg.oereg.com → ACE531246
- `vx.liuxue05.com` → reg.ouyir.com → ACE531722
- `autarchex.com`（Topay 壳，IP 43.249.81.237）→ 直接 url/okx.html → ACE530992

---

## 侦察顺序

1. 首页抽外链 → reg.* / url/okx*.html
2. 跟 302/HTML 跳转；解码 atob reverse 得真实 join/APK 基域
3. HEAD APK 确认 `application/vnd.android.package-archive` + Content-Length
4. join 页脚本：若仅 coinall.ltd/okx.com → 官方拉新页，无私有注册 API
5. 入口 path 扫：admin/api/.env 在静态站无意义；宝塔 WAF 403 ≠ 文件存在
6. 同源扩：`body="ACE53"` / `mxkdpwvhqrn` / `btmzhjpdgxc` / 同 APK CDN

## APK

- 全量下载易超时；用 Range 抽 EOCD/中央目录或 strings 采样
- 真 OKX 壳时渠道在安装归因，dex 内未必有 ACE 明文
- 反编译目标：非官方包才优先找 C2；官方包价值低

## EdgeOne 镜像农场变体（k0.usdtrlc.top 类，2026-10）

不是纯静态 SEO 壳，是 **Tencent EdgeOne 前置的 OKX UI 镜像/反代**：

| 信号 | 例 |
|------|-----|
| 锁面 | `k*.usdtrlc.top` / 随机渠道子域 |
| 跳板链 | aiblog → toprvkx* → jongaccfett?channelId=ACE… → btmrvkxwhpn |
| API | `/api/v5` 活；行情≈真 OKX；登录头 `x-finger-id`/`x-lid` + `needPublicKeyHeader`/`needJwtSign` |
| 登录对照 | `POST /v3/users/login` 与 www.okx.com **同 3901** → **无独立业务后端** |
| APK | `exgglyfor.mpwrs.cn/upgradeapp/android_ACE….apk` ~534–559MB，签 **OK inc.**（正版渠道包，无私有 C2） |
| 裸源 | FOFA 可爆 `47.242.*` 类 openresty 全 403；Lego/EdgeOne TUN 假开端口须 banner 核真 |

### FOCUS=拿后台/壳 时的打法（CRITICAL）

镜像登录墙=真 OKX 同款签名 → **禁止空耗镜像业务面**。改打：

1. **真链导航站**（落地/`sites/*.html` 里的真连，不是友情链）
   - 例：`biquan123.com` = **OneNav 5.56 / WordPress**
   - `action=user_register` **无验证码** → `action=user_login` → `/user/` **用户后台**
   - 投稿 `sites_save` 可写（待审/公开间歇 404 仍算权限成立）
   - REST `/wp-json/wp/v2/users` 枚举超管候选（例 `iowen`）
   - **坑**：`wp-login.php` 可整文件 **PHP 源码泄露**（`Content-Type: text/plain` / 未执行）——立刻拖全量 `.php`
   - WP plugins/themes/upload 常 403；用户面≠超管，别把 `/user/` 当 shell
2. **裸 nginx 易欧 SEO 集群**（FOFA `title="易欧"` + 非 CF IP）
   - 例：`ok15.aigmgmp.cn` @ `8.217.*`；`/admin` 回「域名没有授权」+ QQ
   - robots 泄 `/cache/` `/ebook/`；同 IP 已授权域（例 `grxs.cn`）用 Host 撞
3. OSS/`*.mpwrs.cn` 列目录；EdgeOne Host 绕源（先核 banner，禁把 TUN 假开当 Redis RCE）

### 关联闸（用户会骂）

- **同机** = 锁面 A 记录同 IP（旁口可打）；同 /24 另 IP 不算
- **关联** = 同 IP **或** 首页/JS **真连** 栈
- FAQ/下载页/友情链/sitemap/第三方 IM（zenchat/akey）**不算**
- 无同 IP/真连的外站 admin（例 NameVault `aiaiwww.com`）→ **降权**，短喷负后别空耗

### 判定坑

- `wp-admin`/`ajaxurl` 字样出现在登录页 HTML 里 ≠ 已登录；核验要：跳转离开 `/login` + cookie `wordpress_logged_in_*` + `/user/` 不是登录表单
- OneNav 登录口有限流（`status:2` 请稍后）；注册字段是 `user_login`/`user_pass`/`user_pass2`/`user_mail`，不是 `username`/`password`

---

## 结案话术

- **纯静态 SEO 壳**：入口无 shell/库；报告漏斗节点+渠道号；下一刀 APK/FOFA 或换目标
- **EdgeOne 镜像农场**：明确写「镜像无独立 admin」；若拿到真链导航用户后台，分开报：用户面 / WP 超管 / shell（三栏勿混）
