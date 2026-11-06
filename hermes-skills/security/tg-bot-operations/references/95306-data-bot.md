# 95306 数据机器人实战案例(2026-08-29 会话)

## 系统现状(v7.2)

- 主服 128.241.245.73:12971(海外,密钥登录;私钥备份本机 `C:\Users\Administrator\.ssh\v6_master_key`)
- 采集机 4 台(上海/杭州/广州/成都,国内,已加固:密钥登录+禁密码+防火墙只放主服 IP → 本机直连失效,全部走主服跳板)
- bot @pixshujubot(授权:8002394686 / 7548633061 / 8368000122)
- 数据池 /data_pool:13,174 项目 / 43,870 包件 / 615,259 条报名 / 369,710 供应商档案 / 实时 29 项目包件覆盖率 100%

## 数据池结构

```
/data_pool/
├── index.json           全局索引(历史+live 合并,merger 写时读旧值合并!)
├── health.json          采集机心跳+WAF+竞价中项目
├── 企业档案/<企业名>.json      7,399 家(报名统计)
├── 供应商/<企业名>.json        369,710 家(手机/法人/信用代码/地址)
├── 汇总/                全量18列/自定义查询/实时项目汇总
└── <projId>/
    ├── 项目信息.json / pack_map.json(企业→packId+审核)
    ├── 包件清单.json(公告级,包号/名称/保证金/竞价时段)
    ├── 包件清单_<code>.csv / 企业包件表_18列_<code>.csv
    ├── 公告全文.json(补采/采集时同步抓)
    └── bid_status.json / bid_live.json(竞价状态/出价)
```

## 关键修复案例(同类问题直接照抄)

| 问题 | 根因 | 修复 |
|---|---|---|
| 企业数被覆盖回 0 | merger 重写 index 只统计采集机数据 | `_enterprise_count` 从合并后 pack_map 读 |
| pack_map 企业丢 | merger 覆盖写入 | old_ents 合并 + 新数据覆盖 |
| 历史 index 被挤掉 | merger 重建 index 不含历史 | 读旧 index 合并,只更新 live |
| 公告搜索不到 | notTitle 需精确子串 + 关键词提取 | 多关键词 + 路局名+次数双条件;补采用项目名前 20 字 |
| 心跳 gap 负数 | 采集机 UTC vs 主服 UTC+8 | ±8h 时区容错修正 |
| 分页刷屏 | 每页 sendMessage | editMessageText + 失败降级 sendMessage |
| 收集/加速卡死 | 同步 SSH 阻塞主循环 | threading.Thread 异步 + 完成回调 |
| pkill 自杀 | -f 匹配自身 shell 命令行 | [x] 技巧 + 分两步执行 |
| 命令注入 | f-string 拼口令 | json.dumps(cfg)!r + json.loads |

## bot 命令速查

```
/start 用户中心 | /cal 日历 | /live 实时面板 | /hot 热度
/watch 企业名 | /wh69 快捷 | /q 武汉 废钢轨(条件查询)
/cmp A+B 对比 | /repackall 批量补采(管理员) | /refresh /logs
☰ 菜单按钮: 数据池/竞价/搜索/企业/下载/统计/收集/加速/行情/排行/日历/实时/收藏/历史/监控/对比/授权
```

## 补采链路

```
项目详情 → 🔄补采包件 → 主服 SSH 上海 collect_one.py --pid <projId>
→ 审计抓ST → notTitle搜索(项目名前20字)→ 匹配projId → readNoticeInfo
→ 正则解析包件(第N包/保证金/开启结束) → /tmp/targets/<pid>/包件清单.json + 公告全文.json
→ merger 下一轮(≤5min)自动并入
批量: /repackall 串行 ~15s/项目,29 项目实测 29/29 成功
```

## 加固时间线要点

1. 主服生成 ed25519 密钥 → 分发 5 台 authorized_keys → 测试密钥登录
2. PasswordAuthentication no + PermitRootLogin prohibit-password(sshd -t 先验)
3. 采集机 iptables:recent set→update DROP(60s/6次)→ACCEPT(主服IP)→DROP 其余
4. 密码轮换(禁密码后纵深)+ jumpers.json chmod 600
5. security_watch.py daemon:lastb 增量告警(5min) + 关键文件 sha1 基线(每日)
6. **加固后本机直连采集机被 DROP** → 所有操作经主服(密钥)跳板
