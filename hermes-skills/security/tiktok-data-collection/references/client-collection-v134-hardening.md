# 客户端采集 v1.3.4 增强 + 关键坑（2026-08-29 实测）

tk_ck_gui.py 作品同步通道 v1.3.3→v1.3.4 的实测修正（`C:\Users\Administrator\Desktop\ttck\tk_ck_gui.py`）。

## ★CDP getResponseBody 时序坑（推翻"有头 Chrome 直接可用"的简单结论）
- 现象：滚动循环**每轮实时调** `Network.getResponseBody` → 返回 body 空（长度 0），即使 Network.enable 时设了 `maxTotalBufferSize: 100MB`
- 根因：**响应刚到时（responseReceived 事件后立即）取 body，Chrome 缓冲尚未完成 → 空**；且空结果若被缓存，后续永远取不到
- 正解（v1.3.4 实现）：**滚动循环里只收集 requestId（数 rid 判增长），滚动结束后统一取 body**（此时缓冲完成）——实测通过
- 附加：getResponseBody 每个 requestId **只能取一次**（重复取返回空）——别把取过的 body 缓存的请求再取

## ★200 + content-length:0 = IP 被限流（服务端空响应，与 getResponseBody 无关）
- 判别：CDP 看 responseReceived 的 `headers.content-length == 0`（响应本身空，不是取 body 失败）——**换任何账号（含 @tiktok 大号）都空 = 出口 IP 被 TikTok 临时限流**（同 IP 高频采集账号页触发，15min+ 恢复）
- 与既有"同 IP 高频访问账号页触发临时降级"一致；本会话实证：同一代理 IP 一天内测试 10+ 次 → @tiktok 也 content-length:0
- 处理：等 15min+ 或换代理重试；**别误判成代码 bug / getResponseBody 问题去死磕**

## 作品数据"与实际不符"修复（v1.3.4 + 服务器端）
- 问题：平台"作品数"= 已同步条数（采集不全时 < 实际）；汇总卡=已同步求和（偏小）
- 修复：
  - 客户端滚动增强：滚动直到 **item_list 响应数（rid 数）连续 4 轮无增长**才停（最多 30 轮，1.1s/轮）——替代固定 8 次滚动，尽量采全
  - 客户端解析**真实作品数**：SSR `__UNIVERSAL_DATA_FOR_REHYDRATION__` → `webapp.user-detail.userInfo.stats.videoCount` → 随上传带 `videoCount` 字段
  - 服务器：`TikTokAccount.videoCount` 新字段（schema 加列 + prisma db push）；sync API schema 加 `videoCount: z.number().int().min(0).optional()`；syncVideosFromClient 落库
  - 前端：账号卡"作品数"显示 `videoCount || videos.length`（真实值）；作品网格标题旁显示"已同步 N 条"标注（当 videoCount > videos.length）
- sync API 请求体最终形态：`{"syncToken", "videoCount", "videos": [{tiktokVideoId, title, coverUrl, videoUrl, plays, likes, comments, favorites}]}`（videos ≤200，tiktokVideoId upsert 去重）

## 环境备注
- pybuild venv（%LOCALAPPDATA%\Temp\pybuild）可能损坏（PyInstaller 模块缺失/pip 消失）→ `python -m venv` 重建 + `pip install pyinstaller websocket-client`（PyInstaller 6.22 打包 9.6MB，比旧版小）
- 测试临时 profile 目录（profiles/guest_test*）用完即删，避免残留假会话干扰后续测试
