#!/usr/bin/env python3
"""
快速启动+attach: PyInstaller onefile 子进程刚出现即注入 Frida hook

背景:PyInstaller onefile = 父进程(解压器) + 子进程(真正的 main.dll/网络逻辑)。
子进程启动时可能立刻建立到验证服务器的 keep-alive 连接,所以 hook 必须抢在
连接建立前注入。Windows 上 spawn gating 不可用(frida.NotSupportedError),
用轮询 enumerate_processes 找子进程是最可靠的替代。

用法:
  python fast_attach.py
  (脚本内改 EXE / SCRIPT 路径;SCRIPT 是你要注入的 frida JS,例如 qingyun_spawn.js)

注意:
- 子进程名按目标过滤(示例用 'txmyw' 子串,按实际改)
- 父进程也会 attach 一次(无 main.dll 时轮询脚本会报 not found,属正常)
- 程序自身会持续运行,脚本驻留直到 Ctrl+C
"""
import frida
import subprocess
import time

EXE = r"C:\path\to\app.exe"
SCRIPT = r"C:\path\to\hook.js"

dev = frida.get_local_device()


def on_message(message, data):
    if message.get('type') == 'send':
        print(f'[MSG] {message["payload"]}', flush=True)
    elif message.get('type') == 'error':
        print(f'[ERR] {message.get("description", message)}', flush=True)


def attach(pid, label):
    try:
        session = dev.attach(pid)
        script = session.create_script(open(SCRIPT, encoding='utf-8').read())
        script.on('message', on_message)
        script.load()
        print(f'[+] attached {label} {pid}', flush=True)
        return session, script
    except Exception as e:
        print(f'[!] attach {label} {pid} fail: {e}', flush=True)
        return None, None


proc = subprocess.Popen([EXE])
print(f'[*] launcher PID {proc.pid}', flush=True)

attached = []
deadline = time.time() + 30
while time.time() < deadline:
    try:
        for p in dev.enumerate_processes():
            name = p.name.lower()
            if 'txmyw' in name:  # 改成目标进程名特征
                pid = p.pid
                if pid != proc.pid and not any(a[0] == pid for a in attached):
                    s, sc = attach(pid, 'child')
                    if s:
                        attached.append((pid, s, sc))
                elif pid == proc.pid and not any(a[0] == pid for a in attached):
                    s, sc = attach(pid, 'parent')
                    if s:
                        attached.append((pid, s, sc))
    except Exception:
        pass
    time.sleep(0.2)

print('[*] monitoring...', flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for pid, s, sc in attached:
        try:
            sc.unload(); s.detach()
        except Exception:
            pass
    print('done', flush=True)
