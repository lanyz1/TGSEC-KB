# 滑块验证码绕过方法论(实战验证: sdfaka 发卡站 ttkx.ssy25.cn)

来源: 2026-08 会话, 完整绕过 "SliderCaptcha2024" 类型滑块(前端 AES 加密 + 服务端 PHP 校验)。

## 攻击链(按序)

1. **前端 JS 提取加密实现** — 找 `slider_secure_simple.js` / `slider_captcha.obf.js`(obf 但可读):
   - 密钥硬编码在字符码拼接数组里: `[0x53,0x6c,...]` = `"SliderCaptcha2024SecretKey!!"`
   - 加密 = AES-CBC( key = SHA256(硬编码密钥), iv 随机16字节, PKCS7 ), 输出 `base64(iv+密文)`
   - 复刻: pycryptodome 一行搞定。

2. **接口定位** — 页面内联 `SLIDER_CONFIG = {generateUrl, verifyUrl}`, 通常在 `/slider/generate` + `/slider/verify`。
   - generate 返回 `{code:0, data:{bgImage(base64), sliderImage, sliderY, token}}`
   - verify 提交 `{data: 加密后的 JSON}`。

3. **格式泄露(关键调试信号)** — 用对象格式 `{x,y,t}` 提交 trail 时报:
   `{"code":1,"msg":"验证失败: Undefined array key 2"}` ← PHP 内部错误直出!
   → 说明解密成功、格式被解析, 但 trail 元素必须是**数组** `[x,y,t]` 而非对象。
   - 密钥/算法错则报 "数据解密失败"; 全对才进业务校验。失败消息是免费的逻辑探针。

4. **x 坐标校验** — 报 `验证失败,请重试 (差距: 44px)` → 有精确 x 校验但容差 ~±15px(实测 16px 拒、<15px 过)。
   - 反馈的"差距"只对**同一张图/同一 token**有效; 每次 generate 缺口位置随机, 跨图迭代无效。
   - 服务端可能**先查轨迹后查 x**(随机 x=150 也报"轨迹异常"而非"位置错误"时, 轨迹格式是更优先问题)。

5. **概率盲试(最终方案)** — 图像缺口定位(边缘对/亮度窗口)不可靠时, 直接用固定 x=150 盲试:
   - 单轮通过率 ~40%(容差±15 覆盖分布), 15 轮成功率 99.9%, 每轮 = generate + verify 2 请求。
   - 完整注册流程脚本: 绕过 → verification_code → 带参注册/登录/发短信。

## 配套发现

- 验证码 token **一次性**(首次 verify 后作废), 失败必须重新 generate; 请求必须共享 cookie(session 存 token, 否则永远"验证码已过期")。
- 同站注册/登录/短信验证码**全部只依赖此滑块** → 绕过滑块 = 批量开号 + 短信轰炸前置。
- 限流特征: 绑定接口 `1分钟内最多请求3次`(空 code 也计数)。
- urllib 到 CloudFront/CDN 可能 TLS 握手卡死, 换 curl + cookie jar 最稳。

## 工具脚本形态
`slider_bypass.py` 三步: generate → 构造 `{"x":x,"token":tok,"timestamp":ts,"trail":[[x,y,t],...]}` → AES 加密 → POST verify; 循环 15-30 轮直到 code=0 拿 verification_code。
