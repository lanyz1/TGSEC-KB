---
name: bucket-content-artifact-mining
description: "Use when a readable S3/OSS bucket must be mined."
version: 1.0.0
tags: [pentest, s3, oss, minio, bucket, ocr, artifacts]
---

# Bucket Content Artifact Mining

Class of task: you already hold list+get on a bucket (anonymous ACL, leaked keys, or the app's own upload
endpoint writing into it). Object counts and PII are the obvious finding; the operator's **own uploads** are
the valuable one — browser screenshots naming internal admin panels, spreadsheets of live traffic, and other
attackers' payloads that prove which write path works. Run this before writing the bucket off as a data leak.

## Procedure

1. **Map structure with delimiter listings, not a flat key dump.** At the root and per prefix:
   `?list-type=2&delimiter=/&max-keys=1000`. Keep BOTH `CommonPrefixes` and the root `Contents` — root files
   are usually someone's probes/payloads, not application data. Non-date prefixes (`vaultx/`, `file/`,
   `temp/`, `lvxingtest/`) mark a different upload path and deserve their own listing.
2. **Read the root and every non-date prefix verbatim.** Recognize attacker artifacts by shape:
   `application.yml` / `bootstrap.yml` / `evil.xml` / `rce.xml` that are actually XML (XXE entity blocks, or
   Spring `<bean class="java.lang.ProcessBuilder" init-method="start">`), and write-test markers
   (`_wtest_*.txt`, `test-write-by-*`). A marker from another actor proves some credential can PUT arbitrary
   keys — a live lead even while your own PUT is 403.
3. **Test ACL write bits precisely.** `GET /?uploads` answering `200` with an empty list only proves
   `ListBucketMultipartUploads` is public (read-side); `POST /<key>?uploads` answering `AccessDenied` /
   "Anonymous users cannot initiate multipart uploads" means no write. Never report write access from a 200
   on `?uploads`, and check `?versions` / `?logging` while you are there — versioning off kills config
   recovery, no logging means the attacker's writes left no server-side trail.
4. **Download every image, md5-dedupe, OCR.** `scripts/ocr_bucket_images.py <bucket-url> <prefix>` wraps
   listing → download → hash dedupe → `tesseract -l chi_sim+eng --psm 6` → keyword filter. Operators re-upload
   the same screenshot under many names; dedupe by file hash or the log fills with repeats.
5. **Escalate promising screenshots to vision.** Browser chrome is the prize: the address bar names an
   internal admin host (`test02-admin.<domain>/im/group/group_list`), the title names the product, the
   sidebar names its modules. Resolve that host at once; on NXDOMAIN check WHOIS dates — a domain registered
   recently and already dark is a decommissioned test panel, so record it and move on.
6. **Read operator-uploaded spreadsheets as business intel.** `openpyxl` header row first: viewer lists,
   invite/team hierarchies, payout tables. They map the fraud structure and hand you phone/IP/account columns
   for later correlation without needing another vulnerability.
7. **Count and sample; do not mass-download PII.** Take the total from the paginated listing, sample a handful
   for evidence, keep full pulls out of the case directory, and redact identifiers in the report.

## Rules

- **The app's upload endpoint is a second entry point — measure key control, do not assume it.** Post a file
  with each candidate parameter (`dir`, `type`, `key`, `objectKey`, `ossKey`, `path`, `name`) and judge by the
  returned URL, not by the request. Output pinned to `/uploads/YYYYMMDD/<md5>.<ext>` with every parameter
  ignored means no key control. Filenames carrying a subdirectory (`vaultx/x.xml`) are worth one probe: a
  naive `join(upload_dir, filename)` preserves it. Path traversal (`../`, `%2f`, `%252f`, `....//`, `..;`,
  `%00`, backslash) is usually normalized — if all ten variants land in the dated dir, stop.
- **OCR yield is low and that is fine.** Most images are banners; one operator console screenshot outweighs
  five hundred posters. Run the prefix in the background and grep the log rather than watching it.
- **An attacker payload is a map of the host.** An XXE in `config/application.yml` proves the config service
  parses that key; a Spring-bean `rce.xml` under an upload prefix proves someone believed the app loads XML
  from there. Read the payload's file targets (`/opt/app/application.yml`, `/www/server/redis/redis.conf`,
  `/root/.ssh/id_rsa`) for the filesystem layout before designing your own payload.
- **A same-size identical hash across differently-named config files means one payload, not four findings.**
  Diff by md5 before writing up each root object.

## Support files
- `scripts/ocr_bucket_images.py` — paginated listing → hash-deduped download → Tesseract OCR → keyword hits.
