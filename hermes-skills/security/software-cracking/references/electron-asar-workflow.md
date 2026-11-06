# asar 操作与 PE 检查命令速查

## asar 解包/重打包

```bash
# 解包(需 node/npx)
npx --yes @electron/asar extract resources/app.asar app_extracted
# 重打包(修改后)
npx --yes @electron/asar pack app_extracted resources/app.asar
# 单文件提取
npx --yes @electron/asar extract-file resources/app.asar dist/main/main.js
```

注意:asar pack 后 lint 可能报错(node 尝试执行 electron 文件)— 忽略,不影响打包。

## Electron 应用识别特征

- `app.asar`(核心代码,通常 50-150MB)
- `locales/*.pak`(Chromium 多语言)
- `LICENSES.chromium.html` / `LICENSE.electron.txt`
- `icudtl.dat` / `snapshot_blob.bin` / `v8_context_snapshot.bin`
- `resources/browser/chromium-1223/chrome-win64/`(playwright 内置 Chromium)

## PE 文件类型检查(main.dll 是否可执行)

```bash
file main.dll
# PE32+ executable for MS Windows 5.02 (GUI), x86-64 → 就是 exe,可改名运行
```

Python 读 PE 头:
```python
import struct
with open('main.dll','rb') as f:
    data = f.read(4096)
pe_off = struct.unpack_from('<I', data, 0x3C)[0]
sig = data[pe_off:pe_off+4]           # b'PE\x00\x00'
machine = struct.unpack_from('<H', data, pe_off+4)[0]   # 0x8664=x64
subsystem = struct.unpack_from('<H', data, pe_off+0x5C)[0]  # 2=GUI
```

## VMProtect 加壳识别

- 区段名 `.svmp1` / `.vmp0` / `.vmp1`
- `strings` 无有效输出(字符串加密)
- 导入表只有基础系统 DLL(KERNEL32/ws2_32/USER32...),无业务 DLL
- 编译器时间戳与文件日期一致(打包时间)

## 授权服务器定位(grep 模式)

```bash
grep -oE 'https?://[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' main.js
grep -oE '"[^"]*(license|auth|check|verify)[^"]*"' main.js | head
```

## 中文文件名 zip 打包(Python)

```python
import zipfile, os
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=6) as z:
    for root, dirs, files in os.walk(src):
        for f in files:
            z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), src))
```
- ZIP_DEFLATED 压缩比 STORED 小约一半(1.1GB → ~500MB)
- 中文路径必须用 Python zipfile(系统 unzip 可能 GBK 乱码)
