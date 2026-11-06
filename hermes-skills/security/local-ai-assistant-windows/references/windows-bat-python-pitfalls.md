# Windows 中文环境: bat 编码 + Python 环境混乱

## bat 文件编码 (最重要! cmd 只认 ANSI+CRLF)

**症状**: 双击 .bat 报 `'cho.' is not recognized`、中文全乱码(`瓑寰?`)、命令首字符被吞。
**根因**: write_file 默认写 UTF-8 + LF 行尾。cmd 按 ANSI(GBK) 解析:
- UTF-8 中文 → 乱码
- LF 行尾 + UTF-8 → 每行第一个字符被吞 (`echo`→`cho`, `llama`→`lama`)

**正确做法**: 用 Python 生成 bat, 强制 GBK + CRLF:
```python
content = """@echo off
chcp 65001 >nul
title ...
python app\\main.py
pause
"""
with open(path, "wb") as f:
    f.write(content.replace("\n", "\r\n").encode("gbk"))
```

**校验**: 读取确认 `b"\r\n" in data` 且能 `data.decode("gbk")`。

**双保险**: bat 开头 `chcp 65001 >nul`, 同时 Python 脚本内:
```python
for s in (sys.stdin, sys.stdout):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
```
(有些机器默认 65001 有些 936, 这样两边都稳)

## Python 环境混乱 (ModuleNotFoundError 之谜)

**症状**: 终端里 `python -c "import requests"` 正常, 但用户双击 bat 报 `No module named 'requests'`。

**根因**: 本机 PATH 里 `python` 可能指向 Hermes 自己的 venv
(`C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`),
而 pip install 装的包进了**另一个** venv (如 `D:\xibei\venv`)。两个环境互相看不见。

**诊断**:
```bash
which python                    # 看 python 实际指向
python -c "import sys; print(sys.executable)"   # 确认
```

**规则**:
1. 全程用**绝对路径**调用目标 venv: `/d/xibei/venv/Scripts/python.exe`
2. 装包必须用同一解释器: `/d/xibei/venv/Scripts/python.exe -m pip install ...`
   (不要用裸 `pip`, 它可能绑到别的 python)
3. 给用户的 .bat 里也写死 venv 全路径, 不要 `call venv\Scripts\activate.bat` 然后 `python`
   (activate 可能失败, 且 `python` 会被 PATH 劫持)
4. 测试脚本尽量**纯标准库** (urllib/json), 少依赖 requests 等三方包 —— 双击环境不可控

## 进程残留清理

- 播放音频: ffplay 可能残留(杀不干净), 用 `powershell "Get-Process ffplay -EA SilentlyContinue | Stop-Process -Force"` 循环杀
- 声音来源可能不是 ffplay 而是 SodaMusic(汽水音乐, 注册了 mp3 关联)/系统播放器 → 查 `Get-Process | ? ProcessName -match "ffplay|mpv|vlc|SodaMusic|Groove|wmplayer"`
- 杀进程前**必须先问用户** (用户明确要求)
- 多个 llama-server 实例会挤爆显存/内存 → 只留一个

## 其他

- 用户要"试听多个音频"时, 把所有样本按编号放一个文件夹 + 生成对照说明 txt, 让用户按编号听
- 所有下载任务必须带进度条 (PowerShell Invoke-WebRequest 自带)
