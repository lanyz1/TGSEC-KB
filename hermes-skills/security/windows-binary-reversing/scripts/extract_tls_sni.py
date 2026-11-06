#!/usr/bin/env python3
"""Parse a netsh trace ETL into unique network connections + TLS SNI domains.

Use this when a Windows desktop app (often proxied via v2rayN/Clash) hides its
verification-server traffic: capture with netsh trace, then extract the real
target domains from TLS ClientHello SNI.

Usage:
    netsh trace start capture=yes maxsize=50 tracefile=C:\\temp\\cap.etl
    <trigger the app's login/register/recharge action>
    netsh trace stop
    python extract_tls_sni.py C:\\temp\\cap.etl

Requires: Windows, PowerShell (Get-WinEvent), Python 3.
"""
import subprocess
import struct
import sys


def _ps_dump_frames(etl_path: str, out_path: str) -> int:
    """Dump NDIS-PacketCapture frame bytes (hex) from the ETL via PowerShell."""
    ps = r'''
$events = Get-WinEvent -Path '{etl}' -Oldest -ErrorAction SilentlyContinue |
    Where-Object {{ $_.ProviderName -eq 'Microsoft-Windows-NDIS-PacketCapture' }}
$out = @()
foreach ($e in $events) {{
    $frame = $e.Properties[3].Value  # Byte[] frame data
    if ($frame -and $frame.Length -ge 40) {{
        $hex = [BitConverter]::ToString($frame[0..([Math]::Min(255, $frame.Length-1))]) -replace '-',''
        $out += $hex
    }}
}}
$out | Set-Content -Path '{out}' -Encoding ASCII
Write-Output ("frames: " + $out.Count)
'''.format(etl=etl_path, out=out_path)
    r = subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, text=True, timeout=300)
    print(r.stdout.strip())
    if r.returncode != 0:
        print('STDERR:', r.stderr[:500], file=sys.stderr)
    return r.returncode


def _parse_ipv4_tcp(b: bytes):
    """Return (src, dst, sport, dport, payload_off, payload_len) or None."""
    if len(b) < 14 + 20 + 20:
        return None
    if struct.unpack('>H', b[12:14])[0] != 0x0800:  # IPv4
        return None
    ihl = (b[14] & 0x0F) * 4
    if b[14 + 9] != 6:  # TCP
        return None
    src = '.'.join(str(x) for x in b[14 + 12:14 + 16])
    dst = '.'.join(str(x) for x in b[14 + 16:14 + 20])
    tcp_off = 14 + ihl
    sport, dport = struct.unpack('>HH', b[tcp_off:tcp_off + 4])
    data_off = ((b[tcp_off + 12] >> 4) & 0xF) * 4
    payload_off = tcp_off + data_off
    payload_len = len(b) - payload_off
    if payload_len <= 0:
        return None
    return (src, dst, sport, dport, payload_off, payload_len)


def extract_sni(payload: bytes):
    """Extract SNI from a TLS ClientHello record, or None."""
    if len(payload) < 6 or payload[0] != 0x16:  # handshake record
        return None
    if payload[5] != 0x01:  # ClientHello
        return None
    p = 5 + 4 + 2 + 32  # handshake hdr + version + random
    if p + 1 > len(payload):
        return None
    sid_len = payload[p]
    p += 1 + sid_len
    if p + 2 > len(payload):
        return None
    cs_len = struct.unpack('>H', payload[p:p + 2])[0]
    p += 2 + cs_len
    if p + 1 > len(payload):
        return None
    p += 1 + payload[p]  # compression methods
    if p + 2 > len(payload):
        return None
    ext_len = struct.unpack('>H', payload[p:p + 2])[0]
    p += 2
    ext_end = min(p + ext_len, len(payload))
    while p + 4 <= ext_end:
        ext_type, elen = struct.unpack('>HH', payload[p:p + 4])
        p += 4
        if ext_type == 0 and p + 2 <= ext_end:  # server_name
            sn_len = struct.unpack('>H', payload[p:p + 2])[0]
            q = p + 2
            if q + 3 <= ext_end and payload[q] == 0:
                name_len = struct.unpack('>H', payload[q + 1:q + 3])[0]
                name = payload[q + 3:q + 3 + name_len]
                try:
                    return name.decode('ascii')
                except UnicodeDecodeError:
                    return None
        p += elen
    return None


def main(etl_path: str):
    frames_file = etl_path.rsplit('.', 1)[0] + '_frames.txt'
    _ps_dump_frames(etl_path, frames_file)

    conns = {}
    snis = {}
    with open(frames_file) as f:
        for line in f:
            hexs = line.strip()
            if len(hexs) < 80:
                continue
            b = bytes.fromhex(hexs)
            r = _parse_ipv4_tcp(b)
            if not r:
                continue
            src, dst, sport, dport, poff, plen = r
            key = f"{src}:{sport}->{dst}:{dport}"
            conns[key] = conns.get(key, 0) + 1
            name = extract_sni(b[poff:poff + plen])
            if name:
                snis[name] = snis.get(name, 0) + 1

    print(f"\n=== unique connections ({len(conns)}) ===")
    for k, v in sorted(conns.items(), key=lambda x: -x[1]):
        print(f"  {v:5d}  {k}")

    print(f"\n=== TLS SNI ({len(snis)}) ===")
    for name, cnt in sorted(snis.items(), key=lambda x: -x[1]):
        print(f"  {cnt:5d}  {name}")

    # Filter noise: known library/documentation domains
    noise = ('python.org', 'w3.org', 'sourceforge', 'wikipedia.org',
             'docutils', 'daringfireball', 'opensource.org', 'iana.org')
    suspicious = {n: c for n, c in snis.items() if not any(x in n for x in noise)}
    if suspicious:
        print("\n=== suspicious target candidates ===")
        for n, c in sorted(suspicious.items(), key=lambda x: -x[1]):
            print(f"  {c:5d}  {n}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
