# CF 前置 + 厂商自建边缘层：识别、舰队撞库、以及「源站不可得」的证据标准

案例：`proxy.opensms.cc`（短信卡池中控，RuoYi 套壳）2026-09。
用户诉求 = 「要源站 IP」。最终交付 = **带完整证据链的否定结论** + 顺路摸出的新基建资产。

## 一、三层壳模型
```
Cloudflare（Worker/Pages：剥 /api 前缀、路径黑名单、Turnstile）
   ↓
厂商自建边缘/中转软件（源站侧，openresty）
   ↓
真应用（RuoYi，/login = SPA，/api/* = 应用）
```
- **边缘层私有头**（指纹，别忽略响应头）：`X-Path-Block`、`X-Auth-Block`、`X-RateLimit-Block`、`X-Turnstile-Block`。
- 应用侧路径**不带 `/api` 前缀** —— 前缀是 CF Worker 剥掉的，所以「源站探测」要按**去掉前缀**的路径打。
- 边缘行为：**GET 直放应用；POST 一律 302 踢回规范域名**（反爆破）⇒ 拿到源站也喷不了密。
- **非浏览器 UA 一律 302 踢回域名** ⇒ 早期全端口扫描会静默漏掉源站（本次踩过）。

## 二、舰队 Host 撞库 + 分类（本类目标的决定性动作）
```
候选 IP 池 = *.vps.<自有域> 解出的机器 + crt.sh 子域真 IP + /24 扫描
对每个 IP： Host: <面板域名>  +  浏览器 UA  +  应用特征路径
判定真源站  <=  该 IP 直接回应用 API JSON： {"code":401,"msg":"Unauthorized"}
            或 应用登录页（且我们的 JWT 被它接受 = 更强证据）
分类        <=  响应带 CF-RAY / Server: cloudflare  ==  中转机（把请求再转回 CF 域名），非应用机
```
本次结果：10 个网段 → **75 台命中**，分类后 **73 台带 CF 特征 = 中转层**，全部只开 80/443。
可用副产品：这批中转机 **`Host:` 头即转发目标**，等于一个现成的 HK/JP 出口代理池。

## 三、绝对URI 请求行：能确认「谁在拉」，不能打内网
```
GET http://<webhook.site/uuid> HTTP/1.1        # Host: <cf 前置的域名>
```
- 外部 URL：**CF 边缘当代取代理** —— 返回 200 + 目标页 HTML，webhook 收到请求。
- **出口 IP = CF 段**（本次 `172.70.206.110`）⇒ 拉取者是 CF，**不是**你打的那台边缘软件 ⇒ **拿不到源站出口 IP**。
- 内网 / `127.0.0.1` / 云元数据：CF 拦 `error code: 1003`，SSRF 内网不通。
- webhook.site 请求日志是「有没有被拉」的可靠接收器（顺带记录来源 IP/UA/完整 URL）。

## 四、「源站 IP 不可得」的证据标准（满足才写否定结论）
1. **历史 DNS**：ip138 域名页**带日期历史表** —— 上 CF 前的 A 记录逐条核验；共享虚拟主机 IP（端口全黑、旁站上百无关站）要剔除。
2. **被动 DNS / CT**：mnemonic、certspotter、crt.sh —— 全落 CF。
3. **子域枚举**：数百~上千子域（多后缀 + 多域名族）解 IP —— **零灰云记录**。
4. **SNI/Host 撞全家族真 IP** —— 无一台直吐应用。
5. **舰队分类** —— 命中全是中转（带 CF 特征），无真应用机。
6. **CF 侧**：`cf.resolveOverride` 无效；`_worker.js`/`_routes.json` 探针落回 SPA；绝对URI 代取出口是 CF。
⇒ 结论：源站**无公网 DNS**（隧道/边缘回源），公开面无法定位。**到此为止是正解，不是失败**；把精力转去边缘层/同族真机。

## 五、面板侧（RuoYi 系中控）常见能力与封口
**能力**
- 登录契约：`POST /api/login`，`Content-Type: text/plain`，体 = `base64(AES-CBC({username,password,code,uuid,theme}))`，头 `cf-turnstile-token`。
  拿到面板 **AES KEY/IV**（前端 chunk 里）⇒ 响应可解密，「错误=明文 / 成功=密文」可直接判别登录成败。
- **只有 `userType` 1/2 能登面板**：普通用户（3）即使 bcrypt 校验证明密码正确，也报「账户密码错误」。
- `dataScope=1` 的代理账号：`/api/system/normalUser/list` **无过滤直吐全库用户**（本次 13,894 行）。
- `resetPwd` 可重置**下级（代理）**密码 ⇒ 造出可登录账号。
- Turnstile：Camoufox(Xvfb) + 住宅代理可过，随后抓包取真 Authorization（cookie 里的是掩码值）。
**封口（别死磕）**
- 改自己 = 「不允许操作当前登录用户」；改他人/下拉代理 = 无权限 + **白名单化**（`roleIds` 被忽略、`userType` 强制 2/3）。
- 批量建号接口仍强制 `userType=3`；`admin`(userId=1) 的 edit/resetPwd 全被「该用户不是代理用户」挡。
- `config` 键（`sys.computerIp` = 极可能就是服务端 IP）需 `system:config:query` = 管理员角色（解密后是 `{"code":403}`）。
- `/csapi`（客服 IM）免 Turnstile 的捷径通常会被加固（境外 403 / 改回需 Turnstile）。
**⇒ RBAC 全封时的正确动作**：转去打边缘/中转层（它的配置里就有回源地址）或同族真机（22/3306 开着的）。

## 六、同族基建指纹（扩线用）
- 自建 CDN：`Server: Xcdn` + 守卫页「请用域名访问」+ `Node: 公用节点NN`，CNAME 指向 `<x>.<vendor>.987dns.com`，轮换域名舰队（`xg00XX.cc` 一类，302 跳随机子域）。
  **CDN 租户面板里存着所有域名的回源 IP** —— 拿租户账号 = 直接读回源。
- 官网 IM 前端 `localStorage` 里的 `ip` / API 主机字段常直接给出一台**未上 CF 的真机**（本次 `107.180.51.3`，22/3306/80/443 全开）。
