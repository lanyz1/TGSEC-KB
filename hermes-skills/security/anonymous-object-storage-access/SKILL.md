---
name: anonymous-object-storage-access
description: "Use when S3/MinIO/OSS bucket is anonymously accessible. 对象存储匿名可读/可写桶、列桶、Cognito 匿名换凭据。"
version: 1.0.0
tags: [pentest, s3, minio, oss, object-storage, bucket, misconfig, 对象存储, 匿名桶, 列桶, cognito, 匿名访问, 匿名列桶, 未授权列桶, oss未授权, 存储桶, 公开桶, 公开读, 列目录]
---

# Exposed object storage (anonymous bucket access)

An object store reachable directly — its own port, or an `oss.`/`s3.`/`files.`/`img.`/`r2.` host on
the same origin — is a first-class asset, not a footnote: it holds the app's uploaded media, its
export/backup dumps, and often the *previous* attacker's webshells.

Treat **list / read / write / delete as four separate verdicts.** A bucket is routinely readable
without being writable, and the severity of the four is not the same. Never blur them in a report.

## 1. Find it

- Port-scan the **origin**, not just the CDN host. Console and API usually sit on different ports
  and only one is proxied: MinIO Console on `:9001`, the S3 API on `:9000` (often firewalled, then
  re-exposed through nginx on 443 under `oss.<domain>`). Scan both.
- A hostname like `oss.` / `s3.` / `files.` / `img.` / `r2.` resolving to the origin is a store
  front. Unauthenticated config endpoints leak these names — feed them straight back into recon
  (a leaked `r2Domain` is what puts the bucket endpoint on the map).
- **Signature: the S3 API answers XML, not the app's HTML/JSON.**
  `<?xml ...?><Error><Code>AccessDenied</Code>...<BucketName>x</BucketName>` or
  `<ListBucketResult>` = object storage. Distinguish it from a normal web app before probing.
- **PITFALL — the console port is a SPA and answers `index.html` for EVERY path.** `/`,
  `/.git/HEAD`, `/actuator/env`, `/minio/bootstrap/v1/verify`, `/backup.zip` all return 200 with the
  same HTML shell. That is route fallback, not leakage. Filter on content type / body signature
  before recording a hit, or the entire scan is noise. Probe the **S3 API** (XML) for real
  behaviour; treat the console as a login page only.

## 2. Path-style listing beats the query-string form

The canonical list is `GET /<bucket>?list-type=2`. Behind an edge/WAF the **query string** is often
what gets acted on: on one deployment `?list-type=2` returned a connection reset while the
path-only form succeeded.

```
GET /<edge-prefix>/<bucket>/             -> 200 <ListBucketResult>   works
GET /<edge-prefix>/<bucket>?list-type=2  -> connection refused       edge blocks the query
```

Try both forms before concluding a bucket is closed, and prefer the path form for enumeration.
Fields worth reading: `<Name>` (bucket), `<IsTruncated>`, `<NextContinuationToken>`/`<NextMarker>`,
and per object `<Key>`, `<Size>`, `<LastModified>`, `<Owner><ID>`.
`IsTruncated=false` means you already have the whole bucket — do not imagine a larger store.

## 3. Test the four verbs with self-cleaning evidence

| verb | request | what actually proves it |
|---|---|---|
| list | `GET /<p>/<bucket>/` | `<ListBucketResult>` containing `<Key>` entries |
| read | `GET /<p>/<bucket>/<key>` | file bytes + magic match (`1a45dfa3` mkv/mp3, `52494646` RIFF/wav, `ffd8ff` jpeg, `504b0304` zip) |
| write | `PUT /<p>/<bucket>/<key>` body=unique marker | 200 **and** the key shows up in a re-list |
| delete | `DELETE /<p>/<bucket>/<key>` | 204 **and** the key is gone from a re-list |

**Close the loop on a write.** PUT a uniquely-named marker, re-list and confirm the key count rose
by one, DELETE it, re-list and confirm it is gone. A bare `200` is not a write primitive — the
re-list is. Name the marker so it cannot be mistaken for real data and remove it in the same run.

**Never DELETE a key you did not create.** Enumerating a bucket and clearing it out is destruction,
not testing, and a shared store may be production. Survey first, act on your own marker only.

## 4. Pitfalls

- **`403 AccessDenied` does not mean the bucket exists.** Anonymous callers get the same body for a
  real-but-unauthorized bucket and for a name that was never created, so bucket-name enumeration by
  status code is a false-positive machine. Only `200` + `<ListBucketResult>` proves existence.
  Enumerate **prefixes/keyspaces**, not bucket names. (Many names returning 403 is not "many
  buckets found" — it is one anonymous-denied store answering uniformly.)
- **Do not overclaim from one bucket's contents.** A bucket can hold only the app's *test* fixtures
  while production media lives elsewhere or on another tenant. Confirm the app genuinely writes
  there — upload through the app's own upload endpoint and see whether the object lands in the
  bucket you can list — before reporting "all user uploads exposed".
- **What you find may be the previous attacker's work.** Stored webshells (`.jsp`, `.php`, `.war`,
  `.jspx`, double extensions, `cmd_*` / `shell_*` names), test markers and probe files are evidence
  the store is already known and reused. Report them verbatim; do not execute, fix, or clean up.
- **When the store IS the app's upload target, anonymous write is a poisoning primitive** —
  overwrite user media, or plant a file the app will serve to a victim. Prove capability with a
  benign marker and confirm scope before weaponising.
- CVE-2023-28432 (`POST /minio/bootstrap/v1/verify` env disclosure) applies to the **S3 API port on
  unpatched builds**; on a console-fronted deployment it returns a fallback page or `AccessDenied`.
  Worth one request, never a plan.

## 5. Deliverable

- `loot/<store>_keys.json` — every enumerated key with size and mtime.
- `loot/<store>_files/` — downloaded objects, with the magic-byte verdict recorded per file.
- A one-line verb verdict — `list OK / read OK / write OK (self-cleaned) / delete OK (self-cleaned)`
  — so the next reader sees severity per capability instead of a hedged "bucket was exposed".

## Cognito 匿名换凭据（2026-10 HushChat）
- 小程序/App 配置里的 `IdentityPoolId` + `Region` 可直接 `GetId`/`GetCredentialsForIdentity`，**不需任何登录**
- 拿到 AWS 临时 AK/SK 后按 IAM 权限横向：S3 列桶（用户语音/图片）、SES 发信、DynamoDB
- 判据：配置项同时出现 `PoolId: us-east-1:xxxx` 与 `UserPoolId` = 先试匿名凭据，再试登录
- 落库前先跑 `aws sts get-caller-identity` 确认身份已生效
