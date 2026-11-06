# 95306 Session 9: v6 多机监控系统部署(采集机×4 + 海外主服 + TG Bot)

## 架构(最终形态)

```
🖥 海外主服 128.241.245.73(SSH 12971,Ubuntu22):TG 直连无代理
   ├── merger.py(每5分钟):paramiko sftp 拉 4 台 /tmp/targets → 合并去重 → /data_pool/
   ├── pix_bot_server.py(urllib 直连 TG,multipart 手拼 boundary)
   └── /data_pool/<projId>/{项目信息.json, pack_map.json, 企业包件表_18列_*.csv, 包件清单_*.csv}

🇨🇳 采集机 ×4(上海/杭州/广州/成都,国内低延迟访问目标站)
   └── collector.py(每60s):审计抓ST → 目标发现 → 企业识别 → getBuyPackageList → /tmp/targets/
```

## v6 collector 核心逻辑

1. **目标发现**:`POST /business/bidProject/selectSelfSellList`(pageSize≤100,超了截断)
   - ⚠️ **默认排序不是按竞价时间**——48h 窗口目标在前 100 条里找不到,必须翻 1-3 页
   - ⚠️ `bidStarttime` 格式**无秒**(`"2026-08-31 09:30"`),strptime 需 fallback `"%Y-%m-%d %H:%M"`
   - 发现失败/ST 过期 → **用 state["targets"] 上次目标兜底**,绝不丢目标
2. **企业拦截**:新 ST → user/info(企业名)→ 对每个目标 getBuyPackageList → pack_map.json
3. **包件清单(公告级)**:queryBusinessNoticeList 按 projId 找公告id → readNoticeInfo → notCont 正则
   - `第(\d{3})包[：:](.*?)(?=第\d{3}包|包件具体内容)` + 保证金/开启结束时间
   - **每项目只拉一次**(已有 包件清单.json 且包件数>0 则跳过)——公告不变,避免每轮重复请求
4. **强制目标**:`V6_FORCE` 环境变量逗号分隔 projId;用户后期明确"纯自动发现,不强制盯单项目"

## ⚠️ 部署五大坑(全部踩过)

1. **pkill 自杀 bug**:paramiko exec_command 的命令行含 `collector.py` 字样 → `pkill -f collector.py` 匹配到**自己所在的 shell 并杀掉**,旧进程全活着、命令后半段不执行。
   ✅ 解法:`pkill -9 -f '[c]ollector.py'`(方括号正则技巧,自身命令行是字面量 `[c]ollector.py` 不匹配 `collector.py`)。
2. **双调度冲突**:先部署了 crontab `* * * * * wrapper.sh`,又加了 nohup daemon → 每分钟两个 collector,进程堆积。
   ✅ 解法:只保留一种调度(推荐 nohup daemon:不依赖 cron 服务,海外精简机没装 cron,apt 装又慢)。
3. **ST 过期 → 全部请求卡超时 → 进程堆积**:fetch 目标详情 19 项目 × 多请求 × 20s 超时 = 一轮 19 分钟,daemon 60s 又起新进程,残留 10+ 个。
   ✅ 解法:HTTP 超时降到 8s;已有数据跳过;fetch 包 try。
4. **守护进程计数假象**:`ps aux | grep -c '[c]ollect_daemon'` = 2 不是双进程——是 exec_command 的 `bash -c cd ... && nohup ./collect_daemon.sh` shell + 真 daemon。先 `ps aux | grep` 看明细再判断。
5. **merger 拉取慢**:4 台 × paramiko connect+sftp 每台 1 分钟,一轮 4-5 分钟——daemon 周期 5 分钟刚好。合并"完成"日志出现不代表 CSV 全生成(18列 只写有企业数据的项目;包件清单 CSV 依赖 RAW_DIR 文件已拉全,首轮可能 0,下轮补齐)。

## merger 合并逻辑

- 文件名:`<projId>_pack_map.json` / `<projId>_项目信息.json` / `<projId>_包件清单.json`(中文文件名 sftp 正常)
- 合并:同企业同包件取最新时间戳;包件清单按 packCode 去重
- index.json:projCode/projName/bidStarttime/status/enterpriseCount/packCount

## TG Bot 服务器版(海外直连)

- urllib 直连 `api.telegram.org`(海外机无需代理);multipart 手拼 `--boundary`
- 菜单:数据池索引 → 项目 → 📥18列CSV / 📋包件清单CSV(packfile: 回调)
- 授权白名单 `ALLOWED_IDS`;老头(8368000122)因未对话推送失败 → 用户要求先移除,只留本人+VOKE
- 新用户必须先给 bot 发消息才能被推送(bot 无法主动发起)

## 用户偏好(本会话)

- **随时汇报进度,不要默默跑**;部署过程分步汇报,不要一次性长命令
- 焦点:对**所有即将进行项目**(48h 窗口)完整监控拦截,不纠结单项目(武汉局69次已放弃)
- 不写操作、不留痕;凭据一律脱敏
