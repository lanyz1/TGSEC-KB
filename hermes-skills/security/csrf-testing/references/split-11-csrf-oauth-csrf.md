## 九、登录CSRF与OAuth授权码CSRF（账户劫持级）

### 9.1 登录CSRF深化
```
经典攻击（3.6节）：诱导受害者登录攻击者账户 → 窃取受害者在攻击者账户中填写的敏感信息
高级变体：
1. 登录后服务端不轮换Session → 会话固定（3.6进阶）
2. 登录CSRF + "登录即发邀请码/优惠券" → 攻击者批量薅羊毛
3. 登录CSRF + "新设备风控"绕过 → 攻击者账户无风控标记
4. 登录CSRF + 账户合并/找回逻辑 → 若攻击者账户与受害者手机号/邮箱可关联，反向接管
检测重点：登录接口是否有Token/CAPTCHA？登录后session id是否轮换？是否支持"自动登录"参数（预置token）
```

### 9.2 OAuth授权码CSRF（state缺失/静态）
```
攻击链（Account Linking CSRF → ATO）：
1. 攻击者用自己Google账户完成target.com的OAuth登录流程，在callback前截获 code
2. 诱导受害者访问 https://target.com/oauth/callback?code=ATTACKER_CODE（无需state校验）
3. target.com把攻击者的Google身份绑定到受害者账户
4. 攻击者随后"用Google登录" → 直接进入受害者账户（ATO）

检测步骤：
1. 发起正常OAuth登录，观察authorize请求是否带state参数
2. 若无state / state固定值 / state未在callback校验 → 漏洞
3. 用自己账户完整跑通流程截获code → 在另一浏览器（受害者身份）访问callback → 验证绑定/登录
4. 注意：部分实现callback校验state但不绑定Session（仅检查存在性）→ 同样可利用
```

### 9.3 redirect_uri校验绕过（Code泄露到攻击者域）
```
宽松校验模式与Payload：
1. 前缀匹配 startsWith("https://target.com"):
   https://target.com.attacker.com/callback
   https://<EMAIL-REDACTED>/callback
2. 后缀匹配 endsWith("target.com/callback"):
   https://attacker.com/target.com/callback   （攻击者托管该路径读取?code=）
3. 子域通配过宽 /^https:\/\/.*\.target\.com$/:
   任何可控子域（接管/用户内容托管 pages.target.com/x）
4. open redirect在已允许redirect_uri中：
   redirect_uri=https://target.com/redirect?next=https://attacker.com
   → code经 target.com/redirect 二次跳转携带到攻击者域（URL+Referer双通道）
5. 路径穿越：redirect_uri=https://target.com/callback/../attacker（规范化后越界）
6. 同形字/大小写/端口/尾斜杠规范化差异

验证：替换redirect_uri为恶意值，观察authorize是否放行、code是否到达攻击者监听
```

### 9.4 账户链接（Account Linking）CSRF
```
场景：用户已登录target.com，执行"绑定Google/微信账户"操作
1. 攻击者先用自己的第三方账户发起绑定流程，中途截获code
2. 诱导受害者点击 callback?code=ATTACKER_CODE
3. 受害者账户被绑定攻击者第三方身份 → 攻击者随时用该第三方登录受害者账户
4. 若同时存在"绑定即解锁第三方登录"逻辑，受害者原本密码登录仍然有效但攻击者已获得并行入口
检测：检查绑定接口/authorize是否校验state且state是否与会话绑定
```

### 9.5 新趋势：COAT/CORF与设备码钓鱼
```
- COAT（Cross-app OAuth Account Takeover，USENIX Security 2025）：
  集成平台（工作流自动化/智能家居/LLM插件）中，恶意App可劫持良性App的授权码流→平台级账户接管
  18个主流平台中11个受影响（含Microsoft/Google/Amazon生态）
  检测：平台OAuth架构是否区分App身份、token endpoint是否绑定client_id
- CORF（Request Forgery）：恶意App借平台令牌向第三方API发起伪造请求
- Device Code钓鱼（Proofpoint 2025-12）：利用OAuth设备码流（device authorization grant）诱导受害者授权，
  SquarePhish2等工具自动化；红队可复用于M365账户接管
- OAuth Security BCP持续更新（RFC 9700后续，2026在推进新草案）：
  强制state、严格redirect_uri精确匹配、code一次性+PKCE、绑定client
```

