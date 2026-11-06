# Flutter IM 企业号分服（fchat / mxl / 即联达·轻序协同类）

适用：Flutter `libapp.so` + Go `libgojni.so` 私有 IM；登录前要输「企业号 / 服务器ID / 频道链接 / 网关」。
目标不是喷密码，而是先把 **企业号 → 真 API host** 解开，再跟分服 dump 会员/注册。

## 架构指纹

| 信号 | 含义 |
|------|------|
| Dart 包 `package:fchat/features/server_connect/...` | 连接页：enterprise / channel_link / gateway / QR |
| 符号 `requestFromEnterpriseCode` / `enterpriseCodeNotExist` / `Failed host lookup` | 企业号先做 DNS/自建解析再连 |
| `AppBaseConfig` / `ServerInfo` / `whiteIPs` / `ossHosts` | 基址配置；白名单 IP 与 OSS 域名常一起下发 |
| API：`/app/base` `/app/conf` `/app/ver` `/com/user/login|reg|reset|logout` `/com/sms/send` `/com/oss/sign` `/v2/ws/` | 真网关路径；无 host 时先别喷业务 |
| COS/对象存储：`*.mpk3s.cn` `*.cwiaf.cn` `*.myqcloud.com` Host→403 XML | **壳，不是 API**；停打 |
| APK 内嵌 `RSA PRIVATE KEY` | 多用于配置/通道加解密，**不是**登录口令 |
| Go JNI `Java_mxl_Mxl_getOkHost` / `getCurHost` / `checkApp` / `config` / `http` | 真连接在 `libgojni`（mxl）；Dart 只调 JNI |
| `/v2/ws/%s/%s/%s` | WS 路径模板；host 仍要先 resolve |
| Go 串 `https://` + `.json?t=` + `/v2/app/base` + `GETNETAPP %s` / `线路Base检测` | CheckApp/HostCheck：先拉 OSS 线路 JSON，再探 `/v2/app/base` |
| `Config(app,ossHosts,rsaPri,imei,name,model,ver,os,osVer)`（9 参） | 插件 `channel_mxlsdk` → JNI；`checkApp(app)->String` |

连接入口（libapp 路径）：
- `enterprise_connection_form_view.dart`
- `channel_link_connection_form_view.dart`
- `gateway_connection_form_view.dart`
- `scan_connection_form_view.dart`
- `application/service.dart`（`requestFromEnterpriseCode` / `requestFromChannelLink`）

## 推荐攻击序（非爆破优先）

1. **官网/应用宝/隐私政策** → 下载页、开发者主体、演示企业号、TG 开版号（如 `@imim` / `@kaiban`）。
2. **下 APK**（CDN 403 时：CN 代理 / `--resolve`+SNI / 应用市场直链如 5577 `d11.198324.com/...apk`）。
3. **解 `libapp.so` + `libgojni.so`**：抠域名、路径、企业连接符号；不要把 COS 当网关。
4. **企业号表入库**（用户/开版帖给的 891/886/188888/888626…）→ 只做 resolve 探测，不做密码喷。
5. **真网关判定**：对候选 Host 打 `GET/POST /app/base` `/app/conf`；期望 JSON/业务错，不是 HTML 停放页、不是 301 到无关站、不是 COS 403。
6. **旁路**：开发者站 IP（隐私/ICP）上 MySQL/Redis/管理台；**同公司内容站**（证书/主体同「即联达科技」）上的 Druid/SPA——可出历史注册手机号，但标记为旁路，别当 IM host。
7. 演示号登录后抓 base URL；频道链接/二维码明文 host；mxl `GetOkHost` 深挖。
8. 拿到 `AppBaseConfig`/session 后再 dump 会员/历史注册。

## 误报黑名单（本类任务反复踩）

| 表象 | 真相 | 处理 |
|------|------|------|
| `jild.cn` / `jilianda.com` / `jild24.e.zwz.hk` | 成都「吉联达」隧道/定位，不是 IM 即联达 | 丢弃 |
| `qingxu.cn` 对 `/app/base` 出 500 | 云计费 Yii 壳，路径撞车 | 丢弃 |
| `*.zgym.top` / `*.e.zwz.hk` 企业号子域全解析 | 泛解析到域名停放/CDN 节点 | 先 dig 随机子域；同 IP+同 HTML md5 → 停 |
| `flyx.com` / `yiqixun.me` 邮箱域 | 隐私政策联系域，未必是 API | 可当 OSINT，勿当唯一网关 |
| POST `/app/base` → **200 空 body**（部分反代） | 未进入业务 handler | 换 Host/SNI/真 IP，勿当成功 |
| `jjld.cn` / `applet.jjld.cn` / `s.jjld.cn`（同主体内容站） | 专栏/会员卡后台，**不是** IM `/app/base` 分服 | 可当同公司旁路 dump；企业号 resolve 仍要另找 |

## 同公司内容站旁路（jjld 类）

隐私政策常见「湖北武汉即联达科技有限公司」→ crt/ICP 可能甩出 `jjld.cn`：
- Druid：`/druid/login.html` 默认试 `admin/123456`（classpath 常带 `JJLD_8084`）
- SPA 登录 JS：`{phone: name, password}` 调 `/adminLogin/submit`；UI「用户名」≠ 字段名
- 弱口令命中例：`<PHONE-REDACTED>/111111`（编辑组账号可带超管角色）
- 用户列表：`POST /admin/userInfo/getList` body `{"pageNum":N,"pageSize":500}`
- **分页坑**：`pageInfo.hasNextPage` 恒 false，但 `pages`/`total` 正确 → 按 `pages` 循环
- 头像 CDN：`imgcdn.jjld.cn` / 路径 `xcx.jjld.cn/headImageUrl/...` 多为 COS 壳

详情：`references/jjld-cn-same-company-bypass.md`

## 探测要领

- **泛解析检测**：对 `randomxyz123.<suffix>` dig；若与 `886.<suffix>` 同 CNAME/A，禁止当「分服命中」。
- **Host 矩阵**：同一 IP 上换企业号 Host + `/app/base`；比 status+body md5+Location，不要只看「端口开了」。
- **演示号优先**：公开帖常见 `188888`、`888626`、客服 `888666`；用它们换配置比喷用户密码快。
- **开版 OSINT**：搜「加入服务器」「企业号」「服务器ID」+ 产品名；落地页常藏下载域与默认服 ID（如 wpk「服务器 1314」）。
- **字符串噪声**：Flutter AOT 里 `xxx.im` / `Error.me` 大量伪域名；只保留与 `server_connect` / OSS / cloudfront / 已知产品前缀共现的。

## CheckApp / HostCheck（2026-09 官方 so 实锤）

`libgojni` ADRP+立即数长度还原（非靠字符串边界猜测）：

1. **CheckApp 拉线路**：`https://`(len=8) + `{ossHost}` + `/`(1) + `{name}` + `.json?t=`(8) + `%d` 时间戳  
2. **HostCheck 探活**：对候选线路打 **`/v2/app/base`**(len=12)，期望 HTTP 200（业务 JSON/业务错），不是 COS XML  
3. 同函数附近常出现长度 3 的字面量 `OSS` / `RSA` / `NET` / `APP` 以及格式串 `GETNETAPP %s`、`使用线路: %s`、`线路Base检测: %s` —— **多半是日志/字段名，不是 OSS 对象键**  
4. 对 `qyhtqxxt0813.mpk3s.cn` 等试 `QXXT.json`/`APP.json`/`包名.md5.json`/RSA 密文哈希 → 常见 **NoSuchKey**；`{name}` 算法未破前不要宣称 CheckApp 已打通  
5. **COS 判定矩阵**（必须对照随机 key）：
   - `NoSuchKey`：桶可达、该键不存在  
   - 整桶 `451 UnavailableForLegalReasons`（随机 key 也 451）：合规封桶，**≠命中**  
   - POST→`405 MethodNotAllowed`：不要当成「键存在」；改 GET 读 Code  
6. 官网/Linktree APK 与旧市场包 MD5 可能不同；抠 so 前先对一下 md5，避免在旧二进制上空转

## 与爆破的边界

用户明确反对「只有爆破」时：企业号映射、频道链接、网关 IP、开发者库、演示号、配置下发、CheckApp/`{name}` 还原 全部优先于字典喷。开发者机弱口令仅作补充旁路，且限速；主路径仍是 resolve→config→dump。
