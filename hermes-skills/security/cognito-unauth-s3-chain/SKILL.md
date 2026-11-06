---
name: cognito-unauth-s3-chain
description: >-
 AWS Cognito 未认证身份池换临时凭据打 S3：APK/so/JS 硬编码 IdentityPoolId →
 GetId → GetCredentialsForIdentity → List/Get/Put/Delete。
 用户提到 Cognito、IdentityPoolId、GetCredentialsForIdentity、Unauth Role、
 libne_encrypt.so、S3 匿名列举、头像覆盖、HushChat、KingKong 时使用。
 默认只做到列桶/列对象；覆盖用户对象或批量下载先问。勿与阿里云 AK-SK / 元数据 SSRF 混用。
---

# Cognito 未认证身份池 → S3

**前提**：泄露该池 ID 的 App/站已在 `config/scope*.json`。Cognito/S3 是 AWS 基础设施，**不扩进 targets**。

**成功口径（禁止跳级）**

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | `GetId` 成功（未认证池开着） | 只在 APK 里看到字符串 |
| L2 | 换到 STS 临时钥 + `GetCallerIdentity` | 有 IdentityId 但换钥失败 |
| L2b | `ListBuckets` 或 `ListObjects` | 只拿到密钥 |
| L3 | `GetObject` **一个**非用户对象，或自建 marker 读回 | 全量拖用户头像/语音 |
| L4 | 自建 marker `Put`+`Delete` 成功 | 覆盖真实用户 Key、批量删 |

## 何时启用

- APK/IPA/`*.so`/JS 出现 `IdentityPoolId`：`{region}:{uuid}`
- `awsconfiguration.json` / Amplify / `CognitoIdentityCredentials`
- 角色名含 `Unauth` / `unauth`
- 自定义域 CNAME 到 `*.s3.*.amazonaws.com`，但匿名 List 403（凭据在客户端）

**不要走这张卡**

| 指纹 | 走 |
|------|-----|
| `LTAI` / 阿里云 SK | `阿里云AK-SK利用完整链手法.md` |
| SSRF → `169.254.169.254` | `cloud-metadata-harvesting` |
| 桶匿名 List 200、无 Cognito | `bucket_probe.py` |
| 上传落 OSS 但不执行脚本 | 对象矩阵写格；不当 RCE |

## 强制行为

1. `--app-host` 必须在 scope。 
2. 有临时钥先填对象矩阵：**他人读（列/下）/ 他人写（覆盖）/ 配置（IAM）**。 
3. 默认停在 L2b。自建 marker 证明写权限可以做；**覆盖用户头像/批量 GET 用户对象先问**。 
4. 测完删除自建对象；覆盖过的真实对象必须恢复。 
5. STATUS 不写完整 AK/SK/SessionToken；落 `测绘/cognito_s3/` 本地 JSON。 
6. 加密对象（TEA/xlog）先记元数据泄露，不要假装已解密聊天内容。

## 最短命令

```bash
# 从 APK/IPA/目录抽池 ID（会解压 zip，扫 so/json/plist）
python3 tools/ops/cognito_s3_probe.py extract \
 --path <apk或解包目录> --case <案卷>

# 换临时钥 + 列桶 + 明文/密文分类（需授权 App 域名）
python3 tools/ops/cognito_s3_probe.py chain \
 --app-host <授权App域名> --case <案卷> \
 --pool-id '<region:uuid>' --insecure

# L3：只抽 1 个小明文对象（可复用 creds.json）
python3 tools/ops/cognito_s3_probe.py get-sample \
 --app-host <授权App域名> --case <案卷> \
 --creds-file exports/bot-recovery/<案卷>/测绘/cognito_s3/creds.json \
 --bucket <桶>

# 只证明写：自建 marker 后删除（不覆盖用户 Key）
python3 tools/ops/cognito_s3_probe.py write-probe \
 --app-host <授权App域名> --case <案卷> \
 --creds-file exports/bot-recovery/<案卷>/测绘/cognito_s3/creds.json \
 --bucket <桶> --insecure
```

桶 region 与池不同时加 `--s3-region`；缺省跟 `x-amz-bucket-region` / 301 走。全球 STS 签 `us-east-1`。

## 六步

```text
① APK/so/JS 抽 IdentityPoolId
② GetId（未认证）
③ GetCredentialsForIdentity → STS
④ GetCallerIdentity + ListBuckets
⑤ ListObjects（截断）+ 明文/密文分类；跨区桶跟 301
⑥ get-sample 抽 1 个小明文（L3）；写只用 marker；真覆盖先问
```

## 真源

- 手法：`docs/playbooks/Cognito未认证身份池打S3手法.md`
- 探针：`tools/ops/cognito_s3_probe.py`
- 抽包：`apk-recon` · `apk_recon.py strings`
- 无 Cognito 的裸桶：`python3 tools/ops/bucket_probe.py --help`
- 阿里云长钥：`阿里云AK-SK利用完整链手法.md`
