---
name: platform-backend-triangulation
description: Use when proving one backend or locating the admin panel.
---

# 平台后端归属与后台定位三角测量

## 何时用
- 手上有 3–6 个域名（主站/网关/App API/注册落地/客服），要回答「是不是同一套后台、同一个库」
- C 端已经打穿，后台找不到，需要给出「后台不在自有基建」的**硬结论**而不是「没找到」
- 平台有多套前端（H5 / APP / PC / 代理端），要定哪一个连的是真后端
- 需要把「同团伙/同运营方」从同 C 段的猜测升级成可交付的证据

## 证据强弱（先做最硬的）
1. **Bearer 跨域复用**：A 域 token 打 B 域同名接口，返回同一 user id → 同一用户库。不可反驳。
1b. **行为状态跨域同步（成本 1 发，比 bundle 哈希硬）**：在 A 门把 `admin` 打到锁定，立刻在 B 门用任意口令登录 →
   同一条 `请 N 分钟后再试` 倒计时 ⇒ 同一账号表/同一应用实例（CDN、镜像、克隆站不会同步锁）。
   2026-10 实测：`123.xasftz.cn` 与 `www.rmzcqt.com` 同 bundle、`/api/health` 同形、锁剩余分钟数两门一致
   ⇒ 同后端另一前门，无新攻击面，别再当第二个目标重打一遍。
1c. **存储错误体里的 `BucketName`（数据层铁证，成本 1 发）**：OSS/S3 兼容桶的 `list` 被拒时，XML 错误体常**直接吐桶名**
   (`<BucketName>navbox</BucketName>`)。桶名 = 平台内部代号，硬度接近 token 复用，比 favicon/同 C 段高一个量级。
   一条链就能闭环：**C 端免鉴权 config 端点 → `oss.base.url` → 打该 host 的 list → 报错体吐 `BucketName` = 平台代号**。
   配合前端推导规则 `host.replace(/^([^-.:]+)(-[^.:]+)?/, '$1-oss')`（`tx-h5.x` → `tx-oss.x`）定位真实资源 host。
   实测 2026-10：`db-oss.<d>` 的 list 报 `BucketName: navbox`，与前端 localStorage 键 `NAVBOX_DEVICE_ID` 互印 ⇒ 同平台钉死。
   ⚠ note：list 被拒 **不代表对象不可读** —— 桶根 403/404 时，单个对象常常照样 `200`（实测 `.enc` 842KB 直接拉下），继续试已知 key。
2. **契约头一致性**：`platform` / `version` / `deviceid` 三件套缺一即 4xx，说明同一套 App 后端在收单。
3. **错误形状指纹**：同一 JSON 错误体（如 `{"ok":false,"error":"Not Found"}`）跨域一致 → 同一个 Express/网关。
4. 最弱（只能当旁证）：favicon 哈希、JS bundle 哈希、同 C 段、同证书、同 NS。

## 1. token 跨域复用
```python
for d in DOMAINS:
    r = requests.get(d + PATH, headers={"Authorization": "Bearer " + TOK,
                     "platform": "h5", "version": "1.0.0",
                     "deviceid": "probe"}, impersonate="chrome", timeout=15)
    print(d, r.status_code, len(r.content), r.text[:120])
```
现成脚本：`scripts/same_backend_probe.py <domain1,domain2,...> <path> <token_file>`
判读：200 且同一 `user.id` = 同库；200 但 id 不同 = 两套用户表；401 = 不同鉴权域；CF 403 先过代理再判。

## 2. 错误形状 / 壳体积指纹
同一台/同一套后端会有稳定的「无路由」形态，按体积就能分层：
- nginx 固定 404（常见 548B 纯 HTML）→ 请求没到应用
- 应用 JSON 404（`{"ok":false,...}`）→ 服务在，路由不存在
- SPA catch-all（固定 1438B / 固定的 `<div id=app>` 壳）→ 前端路由吃掉了一切，**不能**据此说「路径存在」
把三层的 code + bytes 记进报告，后面所有排除都引用这套基线。

## 3. 后台定位四组穷举
```bash
# ① 端口（40+ 常用，含 8081/8443/8888/19090）
nmap -Pn -p 21,22,80,443,3000,5000,7001,8000,8001,8080,8081,8088,8443,8888,9000,9090,19090,3306,6379,27017 <ip>
# ② Host 头 vhost（泛解析下必做）
for h in admin manage backend console houtai gly sys boss agent api; do
  curl -sk -o /dev/null -w "$h %{http_code} %{size_download}\n" -H "Host: $h.<domain>" https://<ip>/
done
# ③ 路径矩阵（30+ 条 /admin /manage /backend /console /api/admin ...）
# ④ 网关命名空间（/api/health 有 JSON 时，枚举 /api/<ns>/<resource>，非 404 即记录）
```
判据：
- 所有 Host 都回同一个默认 vhost 壳 → 没有独立后台 vhost
- 所有路径都回同一 SPA 壳或同一 nginx 404 → 后台不在这个前端
- `/api/health` 200 而 `/api/admin/*` 全 JSON 404 → 网关只暴露 C 端
- CT 里只有 `*.domain` 通配证书 → crt.sh/certspotter 永远拿不到真子域，停止刷接口，改从 JS bundle/APK 配置里挖

**C 端配置里的客服入口 = 真实客服系统的泄露点。** `/api/kefu`、`/api/app/kefu`、`/api/config` 这类端点
常直接 302 到第三方多租户客服（带 `channelId`），和页面里嵌入的 SDK 域名可能**不是同一套**。
读 `curl -i` 的 `Location`，那才是运营真在用的后台线。2026-10 实测：前端嵌自有域客服壳，
`/api/kefu` 却 302 到 `https://cau.<随机>.lol/chat/index?channelId=<32hex>` —— 自有域那套只是壳。

## 4. 引流层（cloaking）解码
渠道落地页常是 `https://<cdn>:8443/api/c/<channelId>` 返回的 webpack 壳，壳里 `window.data_char` 是混淆的分流表。单字节 XOR 0x00–0xFF 全试，命中 `"` / `.com` 即停（现成脚本 `scripts/cloak_xor.py`）。
解出的键是流量分组语义：`zhongguo` 国内 / `jingwai` 境外 / `yange` 严格模式（常为空）/ `zhongzhuan` 中转，值是落地域名数组。
- channelId 是随机串，枚举不到别人的页；新 channel 只能从推广链接、客服话术、APK 分享参数取。
- 落地域名「无 A 记录」≠ 不存在：按 UA/IP 动态解析或已烧掉。写「当前无解析」。

## 5. 死域判定（别把 geo-block 当死亡）
| 现象 | 含义 |
|---|---|
| SERVFAIL | 域名/NS 挂了 |
| NXDOMAIN | 没这个名 |
| 解析有 A 但 TCP/TLS 超时 | 被墙 / geo-block / 源站只对特定地区开放 |
先自检本机 resolver：`dig @8.8.8.8 +short baidu.com`；systemd-resolved 偶发全超时时换 `@223.5.5.5` 再判。
多节点交叉验证：`check-host.net/check-http?host=<url>&max_nodes=12` + 轮询 `/check-result/<request_id>`；
只有多区域节点**全超时**才写「实例级不可达 / 仅放行特定源 IP」，单节点超时只能写「本机不可达」。
DNS 有 A 记录 + 全球全超时 + 同域其他子域正常 ⇒ 实例停机或源 IP 白名单，**不写「已关闭/不存在」**。

## ★ 关联性三证闸：先证明「它是我的目标」，再投入

扫段时撞到的高价值邻居（同 /24、同机房、同 CDN、同证书）**默认不是目标**。投入前必须过三发，**缺一发就不许打**：

1. **数据面命中**：拿已到手的**目标全量 dump** 用 `grep -F` 打候选的关键词（appid / 域名 / 平台代号 / 专有名词 / 中文品牌名）。
   **零命中 = 不是同一套系统**，停止推导。
2. **vhost 互通**：拿**目标自己的 Host 头**打候选机的同名路径。回 `530` / 假 CF 页 / 空响应 ⇒ **它不认这个 vhost**，不同源。
3. **目标自己吐出的地址**：唯一能免责的关联锚，是**目标接口/配置/JS 自己返回**的 URL（如 `getinfo` 里吐的域名 → 其 A 记录）。
   从公开扫描里“顺手发现”的 IP **永远不能**当关联证据。

三条全过才继续；**只有「同 /24」一条 = 直接出圈**。

**出圈时的义务**（不做会被追问）：
- 回收自己留下的东西：自建账号停用、改过的配置还原、加的记录删掉，并**回读确认**
- 在回报里**主动明说跑偏**并摆出证据链，不要辩解、不要静默切换
- 用户一句「是我给你的目标吗」问的就是这个 —— 此时先自查关联证据，别先解释工作量

2026-10 实测代价：从目标超级签源站同 /24 扫到一台 Java 后台，数据零命中、vhost 不通、仅同段，却投入了一大轮；
用户一句质疑才发现跑偏，随后要回收自建账号并清理痕迹。**同 /24 是这一行最常见的假关联。**

## 6. 结论模板
> 后台在包网/上游侧，与 C 端不共享 DNS、证书、前端代码。已排除：X 个端口、Y 个 Host vhost、Z 条路径、网关 N 个命名空间，全部回同一默认壳/404。

写「已穷尽排除」并列出排除项，不要写「没找到」。排除完了就换赛道：支付回调域名、客服平台、代理渠道包、上游包网供应商。

## Pitfalls
- **同 /24 不等于同一伙**：共享主机/VPS 商一台机器挂几十个不相干站。**只凭同 /24 投入 = 跑偏**，先过《关联性三证闸》。
- **泛解析 + 通配证书**：`admin/api/mail` 全解析到同一 IP 是通配符，不是发现子域。
- **同 TLD 不同后缀是两个世界**：`jmygw.com` 已 SERVFAIL，`jmygw.vip` 才是活的，别混。
- **SPA catch-all 假阳性**：任何路径都 200 = 前端路由，不是「接口存在」。
- 时间盒：四组穷举一轮 ≤30 分钟，无果即转支付/客服/代理包，别在端口上反复扫。

## 脚本
- `scripts/same_backend_probe.py` — 多域 token 复用探针（带 App 契约头）
- `scripts/cloak_xor.py` — data_char 单字节 XOR 解码 + 分组打印
