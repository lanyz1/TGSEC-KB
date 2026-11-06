# 恶意 Office 宏检测（xlsm/xlsx 查毒）

2026-08-11 实战：用户提供的 `Qavlixor卖家端批量上传商品模板.xlsm` 是木马下载器（伪装 Synaptics 触摸板驱动）。供应商/外部模板先查再开。

## 快速检测流程（不需要打开文件）

```python
import zipfile, re
z = zipfile.ZipFile('file.xlsm')
vba = z.read('xl/vbaProject.bin')          # 宏项目二进制
strings = re.findall(rb'[\x20-\x7e]{6,}', vba)
for s in strings:
    print(s.decode('latin-1', 'ignore'))
```

## 恶意特征（本样本命中项）

| 特征 | 说明 |
|---|---|
| `WinHttp.WinHttpRequest.5.1` / `ADODB.Stream` | 网络下载 + 写文件（下载器标配） |
| `https://www.dropbox.com/...` / `docs.google.com/uc?...&export=download` | 载荷托管在网盘 |
| `ALLUSERSPROFILE\Synaptics\Synaptics.exe` | 释放到系统目录、伪装驱动名 |
| `HKCU\Software\Microsoft\Office\Excel\Security\VBAWarnings` → 写 1 | 自动关闭宏安全警告 |
| `scripting.filesystemobject` / `WScript.Shell` | 文件系统操作 + 执行 |
| 打开时自动执行（`Workbook_Open`） | 不需要用户交互即触发 |

## 结论判定
- 命中 ≥2 条网络/执行类特征 → 判定恶意，**不要打开、不要启用宏**
- 干净模板特征：工作表有真实数据（openpyxl 能看到列头），vbaProject.bin 无网络/注册表/执行字符串
- 空工作表 + 恶意宏 = 典型"带毒空壳模板"，真正的列结构在别处（本案例真模板是另存的 xlsx，见 qavlixor-marketplace 速查）

## 附带处置
- 桌面出现 `~$cache1`、`._cache_*.exe` 等可疑可执行文件 = 宏可能已跑过 → 提醒用户杀毒 + 删除前先确认
