---
name: object-storage-credential-oracle
description: "Use when S3/MinIO creds unknown: AK existence oracle."
version: 1.0.0
tags: [s3, minio, oss, object-storage, credential, accesskey, sigv4, oracle, 对象存储, 凭据判定, 默认口令]
---

# 对象存储凭据存在性 oracle（S3 兼容 / MinIO / Aliyun OSS）

对象存储的**桶存在性**已有专卡（`cloud-storage-bucket-recon`、`anonymous-object-storage-access`）。
本卡只解决另一个轴：**当你手上没有正确密码时，如何先证明「某个 AccessKey 是真的」。**

为什么值得单独成卡：没这一步，弱口令尝试永远是在**盲猜一个可能根本不存在的用户名**，
十几组字典全灭后你会把「用户名是错的」误写成「口令没爆破出来」——两者的后续投入完全不同。

---

## 1. 核心：两条错误码把「AK 不存在」和「AK 存在但密码错」分开

用**合法 SigV4 签名**发任意一个便宜的请求（`GET /` 或 `HEAD /<bucket>`），故意用错的 SK：

| 响应 `<Code>` | 含义 | 下一步 |
|---|---|---|
| `InvalidAccessKeyId` | **AK 不存在** | 换 AK 名；这个名字可以从候选里划掉 |
| `SignatureDoesNotMatch` | **AK 存在，SK 错** ★ | 名字已确认，开始定向口令 |
| `AccessDenied` | AK/SK 都对，但无该操作权限 | 凭据有效，换操作（换桶/换前缀/换 verb） |
| `NoSuchBucket` | 凭据或桶路径有一个不对 | 先用已知存在的桶再判凭据 |

★★★ **`SignatureDoesNotMatch` 是本卡的全部价值**：它在**一个正确密码都没有**的情况下，
证明这个 AccessKey 在服务端真实存在。没有它，「14 组全灭」只能说明「没猜中」，
有了它，「14 组全灭」才是「AK 确认存活、口令未知」——后者才有资格谈优先级和追加投入。

### 必做的对照组（否则结论无效）

单发一次 `SignatureDoesNotMatch` 不算证明 —— **必须证明两类错误是分离的**：

```
AK = 目标名                 -> SignatureDoesNotMatch    (签名算过、key 认得)
AK = 目标名 + "X"           -> InvalidAccessKeyId
AK = 目标名 去掉最后一个字符 -> InvalidAccessKeyId
AK = 随机 10 位              -> InvalidAccessKeyId
AK = 同产品其它常见名        -> InvalidAccessKeyId
```

只有「目标名单独落在 `SignatureDoesNotMatch`、其它全部落在 `InvalidAccessKeyId`」才算证明。
若全部返回同一个码 ⇒ 该面**没有 oracle**，停止这条推理，不要硬套。

### 最小 SigV4 探针（boto3）

匿名/未签名请求回 `AccessDenied`，**它不能用来判 AK** —— 必须真的签。

```python
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

def probe(endpoint, ak, sk, bucket=None):
    s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=ak,
                      aws_secret_access_key=sk, region_name="us-east-1",
                      config=Config(signature_version="s3v4",
                                    s3={"addressing_style": "path"}), verify=False)
    try:
        s3.head_bucket(Bucket=bucket) if bucket else s3.list_buckets()
        return "OK"
    except ClientError as e:
        return e.response["Error"]["Code"]
```

坑：`addressing_style` 必须是 `path` —— 虚拟主机式寻址（`<bucket>.<host>`）在自建/反代部署上
常常**零解析**，会得到 DNS 错误而误判成「服务不可达」。

---

## 2. 先确认目标是自建 S3 兼容（不是云厂商 OSS）

这一步决定后面整套打法：云厂商 OSS 的 AK 是随机串（默认名基本无意义），
**自建 MinIO 的默认 AK 是 `minioadmin`，且部署后极常不改**。

判据（按成本从低到高）：

1. **`X-Amz-Id-2` 响应头**：`dd9025bab4ad...` 前缀 = **MinIO 默认部署 ID**（未改过部署标识）。
2. **错误体形态**：带 `<BucketName>xxx</BucketName>` 的裸 XML（无云厂商的 `RequestId`/`HostId` 结构）。
3. **地域全扫为空**：把桶名在目标云厂商**全地域**跑一遍（阿里云 19 个 region），
   全部 `NoSuchBucket` ⇒ **它不是这家云的 OSS**，大概率自建 → 转 MinIO 默认名假设。
4. 端口：S3 API 常在 `:9000`、Console 在 `:9001`；反代后只暴露 443 的一个前缀。

---

## 3. 桶名被 CDN 重写时，从错误体里把桶名捞回来

反代/CDN 常把 `/` 硬重写成 `/<bucket>/`。此时你打任何路径都被塞进那个前缀，
连「桶叫什么」都不需要猜 —— **错误体里的 `Resource:` 或 `<BucketName>` 会直接告诉你**：

```xml
<Error><Code>AccessDenied</Code><Message>Access Denied.</Message>
<Resource>/navbox/</Resource></Error>
```

同理，`NoSuchKey` 的错误正文常回显**被重写后的完整 key 路径**，
这是判断「CDN 到底加了几层前缀」最便宜的办法，比试 11 种穿越编码划算得多。

**但也要知道这条路的尽头**：同一层重写会把 `../` 归一化掉，
⇒ 管理面 API（`/minio/bootstrap/v1/verify`、CVE-2023-28432）在**路径前缀被重写的部署上物理不可达**，
错误体里会明晃晃写着 `at '/navbox/minio/bootstrap...'`。看到这个就把该 CVE 划掉，别花第二轮。

---

## 4. 尝试纪律（比字典更重要）

1. **先跑 oracle，再动字典。** 顺序反了就是在给一个不存在的用户烧配额。
2. **AK 确认存在后，用「产品相关」而非通用字典**：`<产品名>admin`、`admin`、`root`、`rootuser`、
   `<桶名>`、`<桶名>admin`、`minioadmin`、`<公司缩写>+年份`。通用弱口令表对 root 账号命中率极低。
3. **设硬上限并记下试过什么**（实测 14 组即停是合理量级）。每一组都落盘，否则下一轮会重复烧同一批。
4. **密码对不上就换面**，不要在同一个 AK 上反复加字典 —— 见下条边界。

---

## 5. 边界：拿到写权限 ≠ 拿到你想要的劫持

这一步是最容易过度承诺的地方，必须自证后再下结论：

- **先确认要改的东西真的在这个桶里。** 素材/图片/广告位在桶里 ≠ 安装包在桶里。
  实测过：App 的 IPA/APK 由**超级签/分发平台**下发，桶里根本没有 → 桶写权限**换不了包**，
  只能改视觉层素材。把「能换素材」写成「能换包」是硬伤。
- **区分 raw 桶面与 CDN 面**：对象匿名 GET 200 但 prefix PUT 全 403，是**读公开/写私有**，
  四动词（list/read/write/delete）必须分开报（口径见 `anonymous-object-storage-access` §3）。
- **写权限也不等于接管后端。** 后台登录是另一条独立链（可能压根未部署完），
  桶写权限拿不到 admin token。报告里这两件事必须分开写。

---

## 6. 报告口径

- 凭据状态用三态：`AK 已证实存在 / AK 不存在 / 无 oracle（不可判）`。**不要写「弱口令失败」了事。**
- 附上对照组的完整四行输出（目标名 vs 变体 vs 随机），这是唯一能说服复核者的证据。
- 写权限单独起一行，只写**已实证**的能力（如「可覆写 `/image/**` 素材」），
  并紧跟着写「做不到什么」（如「不含安装包，不含后台」）。

---

## 相关

- 桶/对象四动词分类、云厂商错误码表：`cloud-storage-bucket-recon`
- 匿名读写与列桶、MinIO 控制面：`anonymous-object-storage-access`
- STS 换取与清单挖掘：`object-storage-takeover-mining`

## 案例

- `references/minio-credential-oracle-case-20261026.md` — 自建 MinIO 完整判定链：
  19 地域全扫排除云厂商 → `X-Amz-Id-2` 指纹 → `minioadmin` 对照实验四行读数
  → 14 组定向口令纪律 → CDN 路径重写阻断 CVE-2023-28432 → 写权限边界口径。
