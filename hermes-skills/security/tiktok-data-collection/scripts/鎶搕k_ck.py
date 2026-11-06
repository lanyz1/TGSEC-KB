#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TikTok 登录 Cookie 一键抓取（智能版 v2）
用法：双击「抓tk登录ck.bat」→ 在弹出的 Chrome 里登录 TikTok → 全自动抓取
    - 自动检测登录状态（无需按键）
    - 成功/超时/失败均有 Windows 弹窗提示
    - Cookie 自动复制到剪贴板 + 保存到 ck.txt
配套 bat（GBK+CRLF 编码，勿加 chcp 65001）：
  @echo off
  title TikTok 登录 Cookie 一键抓取
  curl -s -o NUL --max-time 2 http://127.0.0.1:9222/json/version
  if %errorlevel%==0 goto run
  start "" "%CHROME%" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%~dp0profile" --no-first-run --no-default-browser-check https://www.tiktok.com
  timeout /t 3 /nobreak >nul
  :run
  python "%~dp0抓tk_ck.py"
"""
import json, sys, time, urllib.request
import ctypes

try:
    import websocket  # websocket-client
except ImportError:
    print("缺少 websocket-client，请先运行: pip install websocket-client")
    sys.exit(1)

DEBUG_PORT = 9222
TIKTOK_DOMAINS = ("tiktok.com", "tiktokw.us", "tiktokv.com")
POLL_SECONDS = 2
MAX_WAIT_SECONDS = 600  # 10 分钟

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def msgbox(text: str, title: str = "TikTok Cookie 抓取", kind: int = 0x40):
    """Windows 弹窗（0x40=信息图标, 0x10=错误图标）"""
    try:
        user32.MessageBoxW(0, text, title, kind | 0x1000)  # 置顶显示
    except Exception:
        pass


def copy_clipboard(text: str) -> bool:
    """Windows 剪贴板：ctypes 直写（快）+ PowerShell 兜底，重试 5 次"""
    import subprocess
    CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x0002
    # 64 位指针必须声明 restype，否则句柄被截断成 32 位导致写入失败（静默）
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    data = text.encode("utf-16-le") + b"\x00\x00"
    for _ in range(5):
        try:
            if user32.OpenClipboard(0):
                user32.EmptyClipboard()
                h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                p = kernel32.GlobalLock(h)
                ctypes.memmove(p, data, len(data))
                kernel32.GlobalUnlock(h)
                user32.SetClipboardData(CF_UNICODETEXT, h)
                user32.CloseClipboard()
                return True
        except Exception:
            pass
        time.sleep(0.3)
    # PowerShell 兜底
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
            input=text, capture_output=True, timeout=10, check=True,
        )
        return True
    except Exception:
        return False


def http_get_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode())


def get_all_cookies() -> list[dict]:
    pages = http_get_json(f"http://127.0.0.1:{DEBUG_PORT}/json")
    target = None
    for p in pages:
        if p.get("type") == "page" and "tiktok.com" in p.get("url", ""):
            target = p
            break
    if not target:
        target = next((p for p in pages if p.get("type") == "page"), None)
    if not target:
        return []
    ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=15)
    ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == 1:
            ws.close()
            return msg.get("result", {}).get("cookies", [])


def format_ck(cookies: list[dict]) -> str:
    keep = {}
    for c in cookies:
        d = (c.get("domain") or "").lower().lstrip(".")
        if any(d == x or d.endswith("." + x) for x in TIKTOK_DOMAINS):
            keep[c["name"]] = c["value"]
    return "; ".join(f"{k}={v}" for k, v in keep.items())


def get_sessionid(cookies: list[dict]) -> str:
    for c in cookies:
        if c.get("name") == "sessionid":
            return (c.get("value") or "").strip()
    return ""


def main():
    print("=" * 46)
    print("  TikTok 登录 Cookie 一键抓取（智能版）")
    print("=" * 46)

    # 0) 检测调试浏览器
    try:
        http_get_json(f"http://127.0.0.1:{DEBUG_PORT}/json/version")
    except Exception:
        print("❌ 检测不到调试浏览器，请通过「抓tk登录ck.bat」启动。")
        msgbox("请通过「抓tk登录ck.bat」启动本工具。", "启动方式", 0x10)
        sys.exit(1)

    # 1) 等待登录（自动检测 sessionid，无需按键；连续 2 次一致才确认，防半成品）
    print()
    print("⏳ 等待登录 TikTok ...（在弹出的 Chrome 窗口里扫码或输密码登录）")
    print("   登录成功后会自动抓取，无需任何操作。")
    last_sid = ""
    stable_count = 0
    start = time.time()
    while time.time() - start < MAX_WAIT_SECONDS:
        try:
            cookies = get_all_cookies()
            sid = get_sessionid(cookies)
            if sid and sid == last_sid:
                stable_count += 1
                if stable_count >= 2:  # 连续 2 次一致 → 确认已登录
                    break
            elif sid:
                last_sid, stable_count = sid, 1
        except Exception:
            pass
        sys.stdout.write("\r  已等待 %.0f 秒 ..." % (time.time() - start))
        sys.stdout.flush()
        time.sleep(POLL_SECONDS)
    else:
        print("\n⏱ 超时（10 分钟）未检测到登录，请确认已登录后重新双击 bat。")
        msgbox("超时未检测到登录。\n请确认在 Chrome 里登录了 TikTok 后，重新双击 bat。", "抓取失败", 0x10)
        sys.exit(1)

    # 2) 抓取
    print("\n\n✅ 检测到登录，正在抓取 Cookie ...")
    ck = format_ck(get_all_cookies())
    if "sessionid=" not in ck:
        print("❌ 抓取结果异常（缺 sessionid），请重试。")
        msgbox("抓取结果异常，请重新双击 bat 重试。", "抓取失败", 0x10)
        sys.exit(1)

    # 3) 复制 + 保存
    ok = copy_clipboard(ck)
    with open("ck.txt", "w", encoding="utf-8") as f:
        f.write(ck)

    print("📋 剪贴板: %s" % ("✅ 已复制" if ok else "⚠ 复制失败（已保存到 ck.txt）"))
    print("💾 已保存: ck.txt")
    print("→ 去 tiktide.com 绑定账号，粘贴即可。")
    print()
    msgbox(
        "✅ 抓取成功！Cookie 已自动复制到剪贴板。\n\n"
        "下一步：打开 https://tiktide.com\n"
        "登录后 → TikTok 账号 → 绑定新账号 → 粘贴 Cookie（Ctrl+V）",
        "🎉 抓取成功",
    )


if __name__ == "__main__":
    main()
