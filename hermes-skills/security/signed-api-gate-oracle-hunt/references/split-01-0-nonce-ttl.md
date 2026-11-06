## §0 预检:先校服务端时钟(★在判「签名失效/nonce 已消费/TTL 过期」之前)
本机钟偏会让**正确的算法与密钥**恒被判失败,和「签名被作用域绑定」「nonce 一次性」表现得一模一样。
一分钟做掉:`Date` 响应头必须用**出网 HTTP 库**读(页内 fetch 因 CORS 只暴露 safelisted 头,`Date` 恒 `null`;被 WAF 挑战/403 的响应也一样带 `Date`)。
```python
skew = email.utils.parsedate_to_datetime(r.headers["date"]).timestamp() - time.time()  # 本机快为正
# 生成/校验时间戳统一用 time.time() + skew; 先扫 delta ∈ {-1,0,1,2}
# 30s/秒级窗口下「时区」不是有效假设 => 不要一上来扫 ±960
```
多打几台主机(含一个无关大站)比 `Date`,才能判定是本机偏还是目标偏。
> 完整诊断序(TOTP/OTP 同步、字段名以 bundle 为准、两步 bind→enable、尝试计数器纪律)见 `time-sensitive-credential-diagnostics`。

