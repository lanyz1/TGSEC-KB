# Windows bat 编码规则 (中文环境)

## 核心规则

Windows cmd 只正确解析 **ANSI(中文系统=GBK)编码 + CRLF 行尾** 的 bat 文件。

- **UTF-8 编码的 bat** → cmd 把每个中文字节按 GBK 解析 → 中文乱码 (`瓑寰?`)
- **LF 行尾的 bat** → cmd 吃掉每行第一个字符 → `echo` 变 `cho`、`llama-server` 变 `lama-server`、命令被截断
- write_file / 编辑器默认产出 UTF-8 + LF → 直接写 bat 必踩坑

## 正确生成方式 (Python 生成器模式)

```python
content = r"""@echo off
chcp 65001 >nul
title My Script
cd /d D:\project
python app\run.py
pause
"""
path = r"C:\Users\Administrator\Desktop\my.bat"
data = content.replace("\n", "\r\n").encode("gbk")  # CRLF + GBK(ANSI)
with open(path, "wb") as f:
    f.write(data)
```

## 中文显示/输入的双保险

1. bat 开头加 `chcp 65001 >nul` — 把 cmd 窗口代码页切成 UTF-8
2. Python 脚本开头强制 IO 编码:
```python
for stream in (sys.stdin, sys.stdout):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
```

没有这两步,双击 bat 时 `input()` 会因 GBK 字节被按 UTF-8 解码而抛 `UnicodeDecodeError`。

## 验证编码是否写对

```python
data = open(path, "rb").read()
assert not data.startswith(b"\xef\xbb\xbf"), "有 UTF-8 BOM"
assert b"\r\n" in data, "不是 CRLF"
data.decode("gbk")  # 能按 GBK 解码 = ANSI 正确
```

## 关联坑

- bat 里调用 python 时,`python` 命令可能指向错误解释器(见主 SKILL pitfall 7)——用完整路径或先 `python -c "import sys; print(sys.executable)"` 验证。
- 测试中文 API 别用 curl(GBK 字节污染 JSON),用 Python 脚本。
