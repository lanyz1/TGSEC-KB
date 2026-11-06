<!-- archived from /root/.hermes/skills/security/object-storage-exposure/SKILL.md on 2026-10-21 -->

---
name: object-storage-exposure
description: "Use when a bucket/blob store is found in config or JS."
version: 1.0.0
tags: [pentest, recon, cloud, s3, oss, cos, gcs, bucket, exfiltration, data-mining, pii]
---

> 归档卡：原目录 `/root/.hermes/skills/security/object-storage-exposure`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/object-storage-exposure/…')`，不要相对 `references/legacy/` 解析。

# Object Storage Exposure (S3 / OSS / COS / GCS / Azure Blob)

Trigger: a config field or JS constant names a media/CDN base (`mediaServerAddress`, `ossUrl`, `bucketUrl`, `fileServer`), an upload endpoint's response embeds a bucket host, or a bucket name plus key/secret leaks from a config API. The bucket is usually the largest data face of the target and is normally reachable **without any of the API auth** the rest of the engagement is fighting — check it early.

## Always-on rules

1. **The bucket host comes from the config, not from DNS.** A leaked config endpoint or a JS bundle hands you the exact host (`ossimagebu009.oss-cn-hongkong.aliyuncs.com`, `x-bucket.s3.amazonaws.com`, `<bucket>.cos.<region>.myqcloud.com`, `storage.googleapis.com/<bucket>`). Test the anonymous list call on the bucket root before anything else, in both virtual-host and path-style form.
2. **List to completion with NO prefix, and follow the token to `IsTruncated: false`.** The single biggest error is inheriting the app's prefix (`img/`, `upload/`, `./img/`) and reporting its count: a prefix-scoped listing under-reports by orders of magnitude — 61k keys reported where the bucket actually held 1.2M. Pull 1000-key pages, follow `NextContinuationToken` (S3/OSS v2) / `NextMarker` (v1) / `nextPageToken` (GCS) / `NextMarker` (Azure), append each page to a file as it lands, and only call the listing complete once `IsTruncated` is false. That flag is also the arithmetic check on your own total.
3. **Enumerate the bucket-name family, but expect only the referenced one to be public.** Names run `product-word-digits`; zero-padded sibling indices (`...008` / `...009` / `...010`) and suffixes (`-static`, `-img`, `-prod`, `-backup`, `-test`) are worth one short probe. A serial name is a hint the siblings exist, not a promise they are open — do not spend a session there.
4. **Mine the key naming convention before downloading a byte — the path IS the schema.** `<userId>_<timestamp>.jpg` yields distinct uploader IDs with their volume and a time series; `<ts>_<numA>_<numB>_<note>.ext` yields participant pairs and contact names; `ram-mms`, `text.000000`, `part-0`, `*_ext`, `.vcf` mark content pulled off handsets. Derived indexes (distinct users, distinct numbers, pairs, contact notes) cost one pass over the key list and weigh megabytes instead of terabytes — build those first.
5. **Sample for evidence, index for delivery.** Never mirror the bucket. Download a bounded sample (top-N by convention, or a random draw) purely to prove content class and attach as exhibits; the derived txt/csv indexes are the actual loot. Packaging and Excel-format discipline: `engagement-loot-delivery`.
6. **Anonymous list ≠ anonymous read.** Confirm a single known key downloads unauthenticated (`GET` and `HEAD`) and try the ACL/location sub-resources. Providers differ; report exactly which capability you demonstrated rather than calling the bucket "open".
7. **Check for third-party probe artifacts.** A bucket that has been tested before carries other people's `*-probe-*`, `*-poc*`, `pentest_verification_*` files. They date prior access, sometimes name another tester, and are a reportable finding in themselves.

## Procedure

1. Pull the bucket host (and any leaked key) out of the config endpoint and the JS bundles.
2. Anonymous `GET https://<host>/?list-type=2&max-keys=1000` (then the path-style form). Record status, body head, and whether an `AccessDenied` body names a required key.
3. Full paginated listing → `keys.txt`, one key per line. `scripts/list_bucket.py <host> <keys.txt>` does this and is safe to re-run (appends).
4. One pass over `keys.txt`: extension histogram, top-level prefix distribution, per-convention regex extraction, distinct uploader counts, earliest/latest timestamp.
5. Bounded sample download; inspect a couple of text/json files outright and vision-check a couple of images to classify them (persona/marketing material vs. user content vs. someone else's probe file).
6. Aggregate into delivery files (`*_numbers.txt`, `*_pairs.txt`, `*_uploaders.txt`) plus a summary carrying object count, derived PII totals, and time span.
7. Report: object count, derived PII totals, time span, distinct uploaders, access level actually proven, and whether others have been in the bucket.

## Pitfalls

- **An inherited listing is truncated, not complete.** Any count from a prefix-scoped or single-page call is a floor; never write it into a report as the bucket size.
- **Keys can literally contain `./`.** An app whose media base ends `/./img/` produces keys like `./img/<uid>_<ts>.jpg`. Dump the first 20 raw keys and assert on those before filtering — path-normalizing the `./` away hides the entire dataset behind a wrong prefix.
- **Opaque tokens: resuming from the beginning re-collects duplicates.** Persist the last good page token, and dedupe the final file with a set, reporting the unique-key count.
- **XML namespaces differ per provider and per API version.** Match elements by local tag name (strip everything before `}`), never a hardcoded namespace, or `IsTruncated` reads as missing and the loop quietly stops after one page.
- **A 403 on the root is not the end.** Try the path-style form, a known key, and the region-suffixed host — a public-read bucket can deny listing while serving objects fine.
- **Don't mirror.** Pulling over a million objects burns the whole time budget and the transfer limit for no analytic gain over the key list.
