# 95306 bot 可拦截分组 pubtime 静默丢失修复(v6,2026-09-01)

触发:新增项目已入数据池/推送显示"新增项目 1 个",但 bot "可拦截项目·未开始报名"数字不更新。

## 根因

`blockable_projects()`(pix_bot_server.py)四个条件:
1. `all_projects()`(读 index.json)里有它
2. stage ∈ (报名中, 待竞价, 竞价中)
3. `pubtime_map.json[pid]` 发布时间 ≥ DEPLOY_DAY("2026-08-31")
4. enterpriseCount 分流:0=未开始报名,>0=已开始

**`pubtime_map.json` 只有 496 条,一次性批量生成、无自动维护** → 部署日后所有新项目 pubtime 缺失 → 条件 3 不满足 → **静默跳过**(无报错无日志)。影响面:blockable_projects 共 8 处调用(menu_b/mbcat 菜单、搜索范围、mb_monitor_loop 变化推送)——菜单/搜索/推送全失效,不是单个按钮问题。

## 修复(已部署,备份 .bak_v323)

新增 `proj_pub_day()`,三处替换:

```python
def proj_pub_day(pid, info, pub):
    """公告发布日: pubtime_map 优先, 缺则从 projCode 推导(结构 XX+0020+YYMMDD+时间)"""
    pt = (pub.get(pid) or "").strip()[:10]
    if not pt:
        m = re.search(r"0020(\d{6})", str(info.get("projCode") or ""))
        if m:
            try:
                pt = datetime.strptime(m.group(1), "%y%m%d").strftime("%Y-%m-%d")
            except Exception:
                pt = ""
    return pt
```

- blockable_projects:`pt = (pub.get(pid) or "")[:10]` → `pt = proj_pub_day(pid, info, pub)`
- render_mb 显示行 `[5:16]` 同样替换
- 验证:模拟执行 36→37,新项目(a3bb47d1 贵阳车辆段2026年第14次废钢铁)入列,发布时间推导 2026-09-01 正确,py_compile OK
- **重启 bot 才生效**(kill 前需用户同意;验证可先 import/复制逻辑模拟,不必重启)

## projCode 发布时间推导规则

`XX + 0020 + YYMMDD + 时间戳`:OW002026090109122898 → 2026-09-01;OY002026082011210048 → 2026-08-20;OZ002026081816167577 → 2026-08-18。正则 `0020(\d{6})` 精确提取,不会误匹配时间戳段。平台 projCode 统一此结构,可当"项目发布时间"通用来源。

## 调试路径(本次)

1. 用户报"数据池更新了,可拦截-未开始报名没更新"
2. 主服 grep bot 代码找分组逻辑 → 看到 pubtime 条件
3. index.json 查新项目:stage=报名中/live=True/enterpriseCount=0(数据本身正常!)
4. pubtime_map 查新项目:None ← 元凶
5. 其余 2 处 load_pubtime(搜索排序/render 显示)影响小,顺手修显示

## 用户交互教训

- 用户问"以后的项目还会不会出现这样的问题/先回答我" → **先给结构性结论,不要继续深挖**(本次"不要这么麻烦"纠正)。答案:数据池企业数=下界(单企业视角接口 getBuyPackageList 只能答"某账号报了没");全程监控下"审计抓票→用票查报名"闭环,漏抓概率大幅下降,但理论盲区仍在(操作从未被审计捕获的极低频企业);双兜底=竞价结束 bidder 全量 + 结果公示公告。
- 判定"是否全程监控":projCode 发布时间 vs 部署日(2026-08-31);8/29 前发布、48h 窗口才被扫描到的项目不算全程监控(即便今天已结束)。
- targets 状态分布(采集机 /tmp/v6_state.json):13=已结束、19=进行中、22=未到竞价;首批真正全程监控项目 9/4 起结束,9/8 二次挂网是高质量对账样本。
