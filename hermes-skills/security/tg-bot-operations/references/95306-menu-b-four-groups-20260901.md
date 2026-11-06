# 菜单B 四组分组实现(2026-09-01,接 menu-b-realtime 之后)

用户最终划分(替代原三分组 未开始/已开始已拦截/已结束):
1. 🔵 可拦截项目·未开始报名
2. 🟢 可拦截项目·报名进行中
3. 🟡 可拦截项目·报名结束,未结束竞价
4. 🏁 已结束项目

## 判定逻辑(blockable_projects 返回三组)

```python
def blockable_projects():
    """返回 (未开始报名, 报名进行中, 报名结束未结束竞价), 每项=(pid, info)"""
    ps = all_projects()
    pub = load_pubtime()
    not_started, enrolling, pending_bid = [], [], []
    for pid, info in ps.items():
        if info.get("pub_time", "") < pub.get("deploy_at", ""):
            continue                      # 部署前公告的项目不算可拦截(无法从报名开始完整拦截)
        stage = info.get("stage", "")
        ec = int(info.get("enterpriseCount", 0) or 0)
        if stage == "报名中":
            (not_started if ec == 0 else enrolling).append((pid, info))
        elif stage in ("待竞价", "竞价中"):
            pending_bid.append((pid, info))
    return not_started, enrolling, pending_bid
```

要点:
- **stage + enterpriseCount 双字段归类**(用户明确要求"按照要求获取字段归类",不要按其他推断字段)
- 已结束项目仍走 finished_projects()(原逻辑),与可拦截三组并列成四行按钮

## 调用点适配(全部要同步改,漏一个就崩)

| 位置 | 改动 |
|---|---|
| menu_b(cid) 主页 | 四行按钮:`mbcat:{fn}:0 / :1 / :2` + `mb:{fn}:4`(已结束) |
| mb_cat_menu(fn) | 三组分类按钮 `mbcat:{fn}:0/1/2` |
| mbcat 回调处理 | cat 0→未开始, 1→报名进行中, 2→报名结束未结束竞价;show_status 仅 1/2 组显示审核状态 |
| do_mb_search(scope="blockable") | fset 合并三组(旧代码只合并两组,漏 pb 会导致搜索范围缺第三组) |
| mb_monitor_loop 数据变化推送 | 遍历三组拼接(ns+en+pb),不是二元组解包 |
| 搜索提示文案 | "可拦截项目(未开始+已开始报名)"→"可拦截项目(未开始报名/报名进行中/报名结束未竞价)" |

**典型 bug:二元组解包遗漏**——`ns, sd = blockable_projects()` 改成三组返回后,所有调用点都要改为 `ns, en, pb = ...`;搜索/监控/菜单三处最容易漏,改完用 `grep '= blockable_projects'` 全量确认。

## 部署流程(主服 bot)

1. 拉主服 pix_bot_server.py 到本地 → patch → py_compile
2. 上传主服 → pkill 旧进程 → nohup 启动 → **必须验证进程活着**(pkill 后 nohup 启动可能失败,日志显示旧日志不代表新进程在跑)
3. 验证:`pgrep -af pix_bot_server.py` 有输出 + 日志出现 `[PixBot-v3] 启动` + `菜单B监控3min 已启动`

## 重启坑

- `pkill -f pix_bot_server.py && nohup python3 pix_bot_server.py &` 在一条 exec_command 里,pgrep 验证可能返回空(pkill 的 shell 匹配问题)→ **分两条命令执行**,启动后 `pgrep -af` 确认
- 日志 tail 显示旧时间戳 `/start` 回调 ≠ 新进程活着;以"启动横幅 + 定时任务横幅"为准
