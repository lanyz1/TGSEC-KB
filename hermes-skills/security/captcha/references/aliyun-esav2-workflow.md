# Aliyun ESAv2 Slide Captcha Workflow

阿里云滑块验证码 V2 协议（InitCaptchaV2 / VerifyCaptchaV2）。三层防线：设备指纹（feilin）、轨迹行为（VMP 虚拟机）、服务端风控。

## 识别信号

- 接口：InitCaptchaV2 / UploadLog / Log2 / VerifyCaptchaV2
- 域名：`captcha-open-{region}.aliyuncs.com` / `upload.captcha-open-{region}.aliyuncs.com` / `cloudauth-device-dualstack.{region}.aliyuncs.com`
- JS：`aliyun_captcha.js`(225KB 主SDK) / `sg_dynamic.js`(443KB 动态滑块引擎 VMP) / `ali_feilin.js`(581KB 设备指纹)

## DeviceConfig 解密（固定密钥）

- AES-128-CBC + PKCS7，key = `87f879f135f27da7`（固定），iv = `0123456789ABCDEF`（固定）
- 明文按 `#` 分割：`base64(会话密钥)#标志#feilin_token#feilin版本###时间戳#出口IP#标志`
- `fields[0]` = base64 会话密钥（16 字节，用于解 deviceToken）

## deviceToken 解密（会话密钥链路）

- AES-128-CBC + PKCS7，key = DeviceConfig[0] base64 解码，iv = 固定 `0123456789ABCDEF`
- 明文：`SG_WEB|CN_WEB#feilin_token#加密环境(base64)#长度标记#md5`
- 内层环境：`fields[2]` base64 解码 → AES(会话密钥) → 640B → 856B 环境明文（屏幕/UA/插件/字体/IP/时区）

## 轨迹 data 加密管线（VMP 两级）

- 轨迹(x,y,t) → VMP变换1（es 解释器 + 1498 字节码）→ TextEncoder.encode → pako.deflate（549B，zlib 头 0x789c）→ VMP加密2（4/3 扩展 549B→732B）→ btoa（data ≈1016 字符）
- VMP 虚拟机：`es(t,n)` 解释器 5892B + 23 case；字节码 1498 opcode（1-56 操作码，70+ 数据/跳转地址）

## API 链

1. `InitCaptchaV2` → CertifyId + DeviceConfig
2. `UploadLog`（行为日志上报）
3. `Log2`（设备风控日志）
4. `VerifyCaptchaV2` → 提交 `CaptchaVerifyParam{sceneId, certifyId, deviceToken, data}`

## 真人轨迹模板

- 缓出曲线 `x = d*(1-(1-p)^3)`，120-200 点，1.2-2s，4% 概率微停顿回退 1-4px，末端停顿 60-150ms

## 交付

- 纯 Python 解密（cryptography/PyCryptodome 即可）：DeviceConfig/deviceToken 全离线解密
- VMP 管线需会话 JS 上下文（Node vm 沙箱 + es 解释器 + 字节码）
- 浏览器兜底：Playwright 有头 + `--disable-blink-features=AutomationControlled` + 去 `navigator.webdriver` + 真人轨迹
