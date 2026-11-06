## 五、目标平台模式库 - PHP博彩/会员系统

基于对 9581kk.com（必赢/BIYING 模板）的实际渗透，归纳以下通用模式：

### 5.1 典型参数名

| 功能 | 常见参数 | 说明 |
|:----|:---------|:-----|
| 模块路由 | `module`, `method`, `other` | `?module=System&method=first` |
| 登录 | `username`, `passwd`, `vlcodes`, `langx`, `gtype` | gtype=FIRST 固定值 |
| 注册 | `username`, `passwd`, `passwd2`/`repasswd` | 密码规则: 6-12位字母+数字 |
| 会员 | `uid`, `langx`, `gtype` | uid 从 Cookie `SESSION_ID` 取 |
| 支付 | `uid`, `flag` | flag 表示不同支付通道 |
| 验证码 | `yzm.php` | 返回动态单字符（同Session内恒定） |

### 5.2 模块路由发现

```python
# 提取所有 module/method 对
re.findall(r'[?.&]module=([^&\s"\']+)', body)
re.findall(r'[?.&]method=([^&\s"\']+)', body)
```

### 5.3 会员功能探测

```python
# MACenterView 是常见会员中心模块
other_params = ["memberAuth", "userBack", "userAccount", "banktrans", 
                "recharge", "withdraw", "msg", "memberData", "bankSavings", "bankTake"]
```

### 5.4 Session 审计要点

- 检查 `Set-Cookie` 中的 `HttpOnly`、`Secure`、`SameSite` 标志
- 检查是否存在多个 Session Cookie（如 `Example_Session` + `PHPSESSID`）
- 检查 `page_site` 等状态 Cookie 是否可篡改

### 5.5 验证码分析模式

- `yzm.php` 可能返回文本而不是图片（bug/配置问题）
- 验证码值在同一个 Session 内恒定（一次生成多次可用）
- 验证码在 HTML 中可能被注释掉但服务端仍然校验
- 验证码绕过不存在时，可以用 `vlcodes[]` 数组参数触发 PHP 类型混淆

---

