# Tor circuit rotation helper for rate-limit bypass
# Usage:
#   python3 tor_rotate.py check      # tor alive? show current exit IP (via SOCKS)
#   python3 tor_rotate.py rotate     # NEWNYM + settle + show new exit IP
#   python3 tor_rotate.py exits 5    # rotate 5x, print exits (sanity check)
# Requires: local tor with SocksPort 9050 + ControlPort 9051 (no auth).
# For the brute itself: fresh requests.Session + 'Connection: close' after each
# rotation so the new circuit (new exit IP) is actually used.
import socket
import sys
import time

import requests
import urllib3

urllib3.disable_warnings()
SOCKS = 'socks5h://127.0.0.1:9050'
CTRL = ('127.0.0.1', 9051)


def newnym(timeout=10):
    """Signal Tor for new circuits (raw control-port socket)."""
    s = socket.create_connection(CTRL, timeout=timeout)
    s.sendall(b'AUTHENTICATE\r\nSIGNAL NEWNYM\r\nQUIT\r\n')
    time.sleep(0.4)
    try:
        resp = s.recv(512)
    except Exception:
        resp = b''
    s.close()
    return resp


def exit_ip():
    return requests.get('https://api.ipify.org', proxies={'https': SOCKS}, timeout=25).text.strip()


def rotate(wait=2.8):
    resp = newnym()
    time.sleep(wait)
    return resp, exit_ip()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'
    if cmd == 'check':
        print('exit:', exit_ip())
    elif cmd == 'rotate':
        resp, ip = rotate()
        print('newnym:', resp[:60], 'new exit:', ip)
    elif cmd == 'exits':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        seen = set()
        for i in range(n):
            _, ip = rotate()
            seen.add(ip)
            print(i, ip)
        print('unique exits:', len(seen))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
