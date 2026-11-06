# 更新公告自动推送修复 + 关键变化主动推送(2026-09-01 实录)

## 症状与根因:升级 bot 后更新公告不推
- 用户:"更新公告怎么又没推送"。
- 根因:`push_update(version, changes)` 函数**定义了但 main() 零调用点**(调用点在某个版本被删/从未写)。启动日志打印"静默启动,不推送"只是文案,不代表逻辑。
- **教训:函数定义存在 ≠ 被调用;升级后必须验证推送日志 `[更新公告] <版本>` + 授权用户实际收到。**

## 修复模式:main() 启动自动推
```python
# main() 启动处
try:
    _ch = open("/opt/v6/CHANGELOG.md", encoding="utf-8").read()
    _m = re.search(r"## (v[\d.]+)[^\n]*\n(.*?)(?=\n## |\Z)", _ch, re.S)
    if _m and _m.group(1).strip() == VERSION:   # 条目版本匹配才推
        # 30 分钟去重(LAST_PUSH_FILE 记 v+t,重启连推不重复)
        ...
        broadcast(f"🔔 **Pix数据推送助手 {VERSION} 更新公告**\n━━\n{_m.group(2).strip()}\n━━\n👉 发送 /start 查看用户中心")
        json.dump({"v": VERSION, "t": time.time()}, open(LAST_PUSH_FILE, "w"))
except Exception as _e:
    print("[启动] 更新公告推送失败: %s" % _e, flush=True)
```
- 注意:`push_update` 的 changes 参数是 **dict**(分区格式),CHANGELOG 取的是字符串——直接拼文本 broadcast,别硬塞 dict 参数(会 .items() 崩)。
- CHANGELOG.md 只写本次变更(用户硬性要求);旧条目保留但推送只取最新。

## 关键变化主动推送(菜单B 监控线程模式)
用户要"实时更新"时的完整答案 = 链路延迟 + 主动推送:
1. 链路:采集机单轮(瘦身见 monitoring-pipeline-ops/references/poll-slim-and-restart-fixes.md)+ merger crontab */3 + bot index 缓存 30s→5s → 端到端 3-5 分钟。
2. 主动推:daemon 线程每 3 分钟重算**小集合**关键指标(如 39 个可拦截项目的总数/通过/拒绝,只读这 39 个 pack_map,轻量)→ 与上次快照 JSON(mb_monitor.json)对比 → **有变化才 broadcast,无变化静默**(用户约束"不需要每次都推送")。
3. **绝不全库 13K 目录扫描**做周期监控——太重;只监控会变化的小集合。
4. 推送文案:`📊 **菜单B 数据变化**` + 逐项"旧 → 新"(可拦截项目数/审核通过/审核拒绝)+ `👉 发 /menu_b 查看最新`。

## 菜单B 分类判定(数据口径,给用户解释用)
- 可拦截项目 = 公告发布时间(pubtime_map.json)≥ 部署日 + stage∈{报名中/待竞价/竞价中};企业数=0 → 未开始报名,>0 → 已开始。
- 8/31 发布 46 公告 → 39 报名中(可拦截)+ 7 历史(询价/单一来源/谈判/线下类 = 非 bidType=02,merger 自动归历史,排除正确)。
- 已结束三类:有包件清单(完整 12,797)/ 有 pack_map 无清单(部分)/ 无目录(历史索引占位 7,922,8515 快照 2022-2023 老项目 status=14)。12,797 + 7,922 = 20,719 = 已结束总数。
