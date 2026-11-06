---
name: qavlixor-shelf-tools
description: >-
  测绘引擎·Use when Qavlixor 卖家批量上品(素材→Excel→上架工具链)或维护/排障上品工具。含上传两大坑。
owned: true
tier: general
pack: survey-skill
---

# qavlixor-shelf-tools（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-shelf-tools/`

溯源（仅标记）：`hermes/software-development`

---

# Qavlixor 卖家本地批量上品工具链

用户桌面/`D:\跨境商城\会话产物\` 的本地上品工具（素材文件夹 → Excel → Web 界面批量上架到 qavlixor.com）。

## 文件清单
- `素材转上品excel.py` — 素材文件夹 → `素材商品批量上架.xlsx`（16 列模板）
- `qavlixor_shelf_ui.py` — 本地 Web 服务（端口 **8765**）+ 全部上品逻辑（登录/传图/提交/暂停/日志）
- `shelf_ui.html` — 暗色科技风界面（拖 Excel、暂停/继续、常驻详细日志、状态灯）
- `启动上品工具.bat` — 双击启动（ANSI+CRLF，GBK 中文）
- `qavlixor_auto_shelf.py` — CLI 版（备用，同逻辑）

## 素材格式（拓竹类采集素材）
- 每个商品一个文件夹：`01.jpg` 多张图 + `商品信息.txt`
- txt 是 16 列模板字段（`商品标题*:` / `默认价格(USDT)*:` / `SKU明细:` 等，值带 `(注释)` 要去掉）
- 图片列填**本地路径**（工具自动上传，避免外链防盗链）

## 转换规则（用户拍板 2026-08-12）
- 库存全 **9999**（含 SKU 明细每段）
- 运费全改**免运费**（包邮），价格 = 原价 + 首件运费（整机 +60 / 耗材 +8），**SKU 明细价格同步加**
- 状态默认草稿

## ★★ 上传两大坑（修过两轮，必查）
1. **Content-Type**：平台 `/api/uploads` 校验 `file.type`（表单默认 octet-stream 会被拒 "仅支持 JPG、PNG、WEBP 或 PDF"）→ 必须按扩展名显式指定：`.jpg→image/jpeg` 等（requests files 三元组 `("name", f, ctype)`）
2. **URL 字段位置**：上传成功返回 `{ ok, upload: { url } }` ——url 在 **`upload.url` 子对象**，顶层没有 → 取 `data.get("upload", {}).get("url")`，否则误判失败（返回 200 但 url None）

## 服务管理（改代码后必须）
```bash
# 杀旧服务 → 复制新文件到桌面 → 重启
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
cp <会话产物>/*.py *.html /c/Users/Administrator/Desktop/
cd /c/Users/Administrator/Desktop && python qavlixor_shelf_ui.py
```
- 用户报"一直准备中" → curl `/api/state` 看 done/ok/fail/日志（区分真卡 vs 全失败）
- **页面刷新才加载新 html；服务重启才加载新 py**（用户只刷新页面而服务旧代码 = 还是旧行为）

## 平台侧配套（铺货管线）
- `POST /api/admin/products/import-source` 支持 `platform=aliexpress` + `storeName`（店不存在自动 ensureDirectStore）
- **速卖通铺货 `cleanImages=false`**（GPT 清洗会误删干净英文图致"图片不足"跳过；1688 中文图才需要清洗）
- 铺货认证：脚本先 `POST /api/auth/login`（role=admin）拿 `gm_session` cookie；admin 密码哈希曾为占位 "session-auth"（登录 401），需用 lib/password.ts 的 `sha256:salt:hash` 重哈希重置
- 铺货后商品自动进 7 语言翻译管线

## 验证
- 本地全链路：登录 → 上传（拿 url）→ POST /api/seller/products（返回商品 id）→ 清理测试商品
- 清理：DELETE /api/seller/products/[id]（404 可能是商品归属店铺≠登录店铺）
