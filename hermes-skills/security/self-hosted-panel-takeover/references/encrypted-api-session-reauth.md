# 加密响应 / 会话层：解密修复 + 活令牌读面

适用：白标中控（RuoYi 套壳系）登录通了、但每个响应都是密文；或手上有一枚不知道还能用多久的令牌。

## 一、症状与误判
- 症状：`GET /api/...` 返回 200，body 是 base64 密文（响应头常见 `x-encrypted`），怎么解都是乱码/异常。
- 典型根因**不是**密钥算法错，而是**手上那份 KEY 被抄错一个字符**（前端混淆/人工转录都易错）。
  本次案卷存的串是 `…K+tFdvJ4=`，真串是 `…Kt+FdvJ4=` —— 差一个字符，全部响应解不开，白卡一整轮。

## 二、四步判读（按顺序省钱）
1. **先测密文是否恒定**：同一接口换参数、或换另一个接口，密文一模一样 ⇒ 那是**固定拒绝体**（无权限/参数错），
   不是「没解密成功」。此时去挖权限面，别去爆破密钥。
2. **定位密钥来源**：前端 bundle 里找加解密工具（`aes-util.js`、`crypto-js` 包装、`CryptoJS.AES.decrypt`），
   拿到 KEY/IV 的 base64 字面量；与案卷里存的**逐字符 diff**（常见错法：相邻字符换位/漏 join 符号）。
   **验收标准：两个不同请求同时解成功**（同一份密钥解一个成功可能是碰巧）。
3. **判 Token 类型，再决定要不要伪造**：
   ```python
   import base64, json
   payload = seg1_of_jwt.split('.')[1]
   json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
   ```
   - 载荷含 `login_user_key`（uuid）+ `sub` = **RuoYi**：会话在 Redis，签名不是关口 ⇒ **伪造 JWT 无意义**，别写这个脚本。
   - 载荷是自签的（`uid/role/exp` 且服务端只验签名）= 有 `JwtSecret` 就能伪造任意身份（转去看源码/配置拿 secret）。
4. **读有效期**：解出的令牌/会话带过期时间（本次活令牌还剩数天）。**把「还能读多久」写进报告**，并按需要定时续用。

## 三、活令牌的读面清单（先扒这些，都是即时战果）
`/api/devicemessage/config/list`（卡池设备短信）· `/api/system/agent/list`（代理+`loginIp`，常是 CF IPv6）·
`/api/system/user/list`（`dataScope=1` 时全库）· `/api/message*/list`（消息/OTP 批次）· 菜单/字典接口列全平台端点。
- 拿到列表后**统计 + 取样**（条数、最新 `updateTime`、号段、话术原文）——「今天 16:58 还在发」这种时间戳才是活证据；
  只报「能读库」没有说服力。
- 同一批数据里 `loginIp` / 号段 / 时区能反推他们客户的来源国家与线路。

## 四、403 的正确解读
响应 `{"msg":"没有权限，请联系管理员授权","code":403}` = **解密和鉴权都对了，是权限面不够**。
⇒ 转打边缘层/真机集群（见 SKILL.md 第一步半），别回去再试解密或伪造令牌。

## 五、前端 bundle 挖矿（别用内联 shell grep）
Minified JS 是单行超长文本，**内联 grep/sed 带嵌套引号会连续翻车**（本次挂了两次）。写成 `.py` 跑：
```python
import re, collections
s = open(js_path, encoding='utf-8', errors='ignore').read()
print(collections.Counter(re.findall(r'https?://[a-zA-Z0-9._:/?=&%-]{4,80}', s)).most_common(30))
print(collections.Counter(re.findall(r'[`"\'](/[a-zA-Z0-9/_.-]{3,60})[`"\']', s)).most_common(60))
for kw in ['token','login','/api','xboard','board','clash','v2ray','ws://']:
    n = s.lower().count(kw)
    if n: print(n, kw)
```
产出用途：① 找 API 基址（`http://localhost:4000/api` 这类 dev 串能反推生产端口）；② **路由即产品类型**：
`/accounts /portfolio /transactions /prices/refresh` = **假投资/交易盘**；`/login + sys_menu` = 中控；
`/c/ /s/ /sub/` = 订阅面板。同一台/同舰队上挂多种诈骗产品线时，这份映射帮你分清谁是谁、分别算战果。
③ 完全没有 IP/回源域名（本次 56 chunk + 全 JS 零 IP）也是结论：**源码面已穷尽**，可写进报告。

## 六、归属核验（交付前必做）
- 我方为测试自建的 CF Worker/账号（`*.workers.dev`、`cfat_` token）**不是目标资产**，只能当探针写。
- 托管商同段其他租户（宝塔纯净版/ThinkPHP 商城/Looking Glass）**不是目标**：识别出来就收手，报告里明确剔除。
