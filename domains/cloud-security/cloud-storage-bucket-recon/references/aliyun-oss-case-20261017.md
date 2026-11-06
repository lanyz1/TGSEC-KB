# Aliyun OSS case — badiao / 新CC (2026-10-17)

Context: APK `com.zk.rbchat` (RainbowChat shell) leaked custom OSS domain `oss.497e.cn`; API host `api2.497e.cn`. Goal was the user DB; OSS was the backup/source-leak candidate.

## Buckets found

| Bucket | Region / endpoint | Listing | Random object key | Verdict |
|---|---|---|---|---|
| `cc12348` | cn-beijing, but OSS endpoint returns `PublicEndpointForbidden` | via `oss.497e.cn` -> `AccessDenied: The bucket you access does not belong to you` | avatars `avatar/<uid>/<yyyymm>/<uuid>.jpg` -> 200 image/jpeg | main media bucket; objects public via CNAME only |
| `ccdata` | cn-hangzhou | 403 `Anonymous user has no right...` | `NoSuchKey` | **object-public**; 200+ deterministic keys all missed |
| `ccapp` | cn-shenzhen | 403 | `NoSuchKey` | object-public; referenced in RN bundle |
| `ccim` | cn-shanghai | 403 | `NoSuchKey` | object-public |
| `cc-backup` | **eu-central-1** | 403 `Anonymous user has no right...` | 403 `...because of bucket acl` | **private; strongest DB-dump candidate** |
| `ccbackup` | cn-shanghai | 403 | n/a | private |
| `cc-oss` | cn-shanghai | 403 | n/a | private |
| `xincc`, `ccfile`, `ccstatic` | endpoint not captured | 403 | n/a | exist; unclassified |

Nonexistent (404 `NoSuchBucket`): `cc12348-backup`, `xincc-backup`, `badiao`, `497e`, `cc-im`, `ccdb`, `ccsql`, `cc12348-test`.

## Exact error strings that matter

- `Code>NoSuchBucket` -> name free.
- `Code>AccessDenied` + `Message>The bucket you are attempting to access must be addressed using the specified endpoint` + `<Endpoint>oss-eu-central-1.aliyuncs.com` -> **region mismatch, not private**. This was the key discovery: a Beijing request to `cc-backup` looked like a 403 "exists but private", but the bucket is in Frankfurt.
- `Code>AccessDenied` + `Message>The bucket you access does not belong to you.` -> anonymous List denied (bucket ACL private), even through the CNAME.
- `Code>AccessDenied` + `Message>You have no right to access this object because of bucket acl.` -> object itself private.
- `Code>PublicEndpointForbidden` + `Message>Not allowed using the OSS public endpoint, please use CNAME instead.` -> only the bound custom domain works.
- `Code>NoSuchKey` -> anonymous object GET is allowed; key missing. This is the green light for key guessing.

## Key guessing (all missed)

- Dates 2026-04-01..2026-10-17 x `cc_<date>.sql`, `cc<date>.sql`, `<date>.sql`, `backup_<date>.sql`, `db_<date>.sql`, `cc12348_<date>.sql`, `backup/<date>.sql`, `sql/<date>.sql`, `db/<date>.sql`.
- Names: `backup.sql`, `db.sql`, `data.sql`, `dump.sql`, `users.csv`, `users.sql`, `user.csv`, `members.sql`, `config.json`, `.env`, `database.json`, `index.html`, `robots.txt`, `manifest.json`.
- App paths: `apk/app.apk`, `apk/c.apk`, `apk/latest.apk`, `app/version.json`, `app/config.json`, `2.0.0/app.apk`.
- Result: 200+ requests, zero 200. Object keys are UUID/business paths, not date/name based.

## Pivot that was queued (blocked by WAF)

- Client endpoint `file/getBigFileUploadInfo` (raw JSON, not the AES envelope). Sending `{file_md5: <md5>}` first returned `缺少文件指纹`; after adding `file_md5` it returned `retCode: 0` without visible STS in the truncated response. Full response/field fuzz was not completed because the API IP was WAF-banned.
- Unverified candidate: if the full response carries `accessKeyId/accessKeySecret/securityToken`, use that STS to list `cc-backup` (eu-central-1). Do not present this as a confirmed STS leak until re-tested.

## Ops lesson

- `cc.badiao.cn` (47.76.234.20) and `api2.497e.cn` (47.98.217.136) are different hosts; OSS is a third surface. Enumerate all three independently.
- A `gobuster` run of ~38k requests against `/api` got the source IP banned at TLS level on all ports for >1h, which blocked the STS test. Keep storage/API probing low-rate and separate from directory brute.
