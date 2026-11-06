# 2026-08-12 上品工具上传契约 + 素材 txt→Excel 转换

## ★上传 API 契约（/api/uploads，任何自动上传脚本必读）

两个坑（自动上品工具实测踩到，全部商品失败后才定位）：

1. **Content-Type 必须显式指定**：平台按 `file.type` 校验（`allowedTypes.has(file.type)`），
   Python requests 默认 `application/octet-stream` → 拒收"仅支持 JPG、PNG、WEBP 或 PDF"。
   修复：按扩展名传三元组 `files={"file": (name, f, ctype)}`，
   ctype = `.jpg/.jpeg→image/jpeg`、`.png→image/png`、`.webp→image/webp`。
2. **返回 URL 在 `upload.url` 子对象**：成功响应 `{ok:true, upload:{id,name,type,size,url,storageProvider}}`，
   顶层**没有 url 字段**。解析必须 `data.get("url") or (data.get("upload") or {}).get("url")`，
   否则误判"上传失败"（200 但 url=None）。

排障套路：上传被拒/误判失败时，先 curl 手动复现拿完整响应体，对比返回字段结构，
不要只盯着状态码（200 也可能字段没读对）。

## 素材(1) → 批量上品 Excel 转换（商品信息.txt 16 列解析）

素材目录结构：`素材(1)/{套装|打印机|耗材}/{商品slug}/01.jpg... + 商品信息.txt`
- 商品信息.txt 每行 `字段: 值`，值尾部有 `(注释)` 需正则剥掉（`\s*\(.*?\)\s*$`）
- 分类列带 `  ※平台暂无3D打印机分类,需管理端新增` 尾巴 → replace 掉
- 图片列填**本地路径**（工具自动上传，比 Amazon 外链稳）——主图=第 1 张，详情=`;` 连接全部
- 用户偏好：库存全 9999（含 SKU 明细列）、全店包邮（运费方式=免运费）、
  **运费折进售价**（价格=原价+首件运费；SKU 明细价格同步加；整机原首件 60、耗材 8）
- 转换脚本：`D:\跨境商城\会话产物\素材转上品excel.py`（openpyxl 输出 16 列 xlsx）

## 本地上品工具（qavlixor_shelf_ui.py + shelf_ui.html + 启动.bat）

- 架构：ThreadingHTTPServer(:8765) + 前端轮询 `/api/state`；任务线程内 STATE 单例
- bat 以 `cd /d %~dp0` 启动同目录 py（3 文件必须同目录）
- 改代码后**必须重启服务进程**（用户双击 bat 的旧进程跑旧代码；杀端口 8765 占用者再启动）
- 用户端"一直准备中"= 任务在跑但全失败（current 显示的是最后一个处理项）→ 看 /api/state 的 logs
- 清理：测试商品 DELETE 接口可能 404（商品归属店铺校验），残留草稿无害可留

## v3 UI 迭代（2026-08-12 尾）：详细日志面板 + 暂停/继续

用户两次报"一直准备中"后要求"页面底下加详细日志"+"加暂停按钮"。三处联动改：

- **后端细粒度日志**：每个商品 3 条步骤日志（`[n/47] 处理中` → `[n/47] 图片 上传 x 张` → `✅/❌ [n/47] 商品名 … 建品成功/失败原因`），STATE.update 每次**全量覆盖 logs 数组**（单例小数组，前端按 lastCount 增量追加）
- **常驻日志面板**（html）：独立 card 放页面底部（不复用进度区的 logs，避免 id 冲突）；状态灯 `.dot`（run=绿闪 `@keyframes pulse` / pause=黄 / done=蓝 / err=红）+ 状态文字 + 日志计数；每条日志带 `HH:MM:SS` 时间戳；**页面加载即 `setInterval(poll, 1200)`**（任务前后都轮询，任务结束**不** clearInterval——常驻显示结果；开始按钮也不再新建轮询，防双轮询）
- **暂停/继续**：后端 `STATE.paused` 标志 + 任务循环顶部 `while STATE.paused: time.sleep(0.5)`（原地等待不烧请求）+ GET `/api/pause` `/api/resume`；前端主按钮旁加暂停按钮（任务运行时显示，disabled 反转，文字 ⏸暂停↔▶继续）；poll 里 `data.paused` 分支驱动状态灯与按钮文案
- 按钮行布局：`#go` 改 `style="flex:1"` + 暂停按钮 `flex:0 0 auto`（渐变主按钮 + 白底次按钮并排）
- 验证：`curl /api/state` 看 `paused` 字段 + 页面 grep `pauseBtn|/api/pause|setStatus`；**服务重启后旧任务仍可能挂在旧进程**——先 `Get-NetTCPConnection -LocalPort 8765` 杀占用者再起新进程

## 木马驻留追加（2026-08-12 第二次清除）

- `C:\ProgramData\Synaptics\Synaptics.exe`（PID 34484）为宏木马释放的驻留进程
- 清除：Stop-Process -Name Synaptics -Force → rm -rf C:\ProgramData\Synaptics
- 检查无残留：服务（Get-Service）、注册表 Run（HKCU+HKLM）、计划任务、WMI 订阅（root\subscription）
- 桌面恶意 .xlsm 会在工具把 .xlsx 复制到桌面后**同名替换**（替换机制：删 .xlsx 放 .xlsm）——
  交付 .xlsx 后必须 zipfile 验证（无 vba 条目），发现 .xlsm 即视为恶意（.xlsx 格式不可能带宏）
