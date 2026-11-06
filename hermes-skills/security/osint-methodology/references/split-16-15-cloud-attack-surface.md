## 15. Cloud Attack Surface

### 15.1 Bucket permutation

Build candidate bucket names from: target's root domain, subdomain stems, optional brand/company name. Filter generic stems unless combined with target-identifying tokens. Apply 6 prefixes × 15 suffixes (companion skill §16.8 has the lists).

### 15.2 Provider URL templates

S3, GCS, Azure Blob templates — see companion skill §16.8.

### 15.3 Probe technique

- HEAD first. Status code 200/301 = exists; 403 = exists, private; 404 = skip.
- If exists, GET on bucket root. Listable XML/JSON listing → **CRITICAL**.

### 15.4 Severity mapping

| Outcome | Severity |
|---|---|
| Bucket listable | CRITICAL |
| Bucket exists, objects readable by direct URL but not listable | HIGH |
| Bucket exists, ACL private | INFO |

### 15.5 Adjacent cloud signals

Extract AWS account-ID from S3 region/error responses. GCP project ID from GCS error responses. Azure tenant ID from blob URL patterns.

---

