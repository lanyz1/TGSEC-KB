# Pix Bot v7 会话实录(数据池整理 + 补采 + 归一化 + 加固)

2026-08-29 会话,在 v3(查询工坊/跳板机管理)基础上继续迭代。附属于 tg-bot-ops。

## 查询工坊三级挑选(下载"随心所欲")
- 条件筛选(18路局×13物资×4状态×7时间)→ **勾选项目**(分页 10/页,跨页累计,已选数实时显示)→ **挑字段**(全字段18列/精简/仅项目/仅企业/仅包件)→ 生成 CSV 下载。
- 回调:`qry/qrybureau/qryset:{field}:{idx}/qryrun/qrysel:{pid}/qrypage:{n}/qrydl:all|sel/qrycols/qrycolset:{name}`。
- 查询状态存 Q_STATE[cid]:{bureau,type,status,date,matched[],selected[],page,cols,msg_id}。
- 结果过大限制 >1500 项目提示加条件;生成/发送全部后台线程(`_do_qrydl`),完成后自动发文件 + 50MB 检查。
- 分页编辑原消息(存 msg_id),edit 失败自动降级新消息(见 SKILL.md 陷阱 3)。

## 补采包件(采集漏包件时的自助补采)
- 采集机 `collect_one.py --pid <projId>`:跳过关键词搜索,直接按 projId 找公告(先读 /tmp/targets/<pid>/项目信息.json 拿 projName → notTitle 搜索匹配 → 翻 3 页兜底)→ readNoticeInfo → 正则解析包件(第\d{3}包/保证金/开启结束时间)→ 落盘 包件清单.json + 公告全文.json。
- bot:项目详情按钮 `repack:<pid>` → 后台 SSH 采集机执行 → 完成通知;管理员 `/repackall` 批量补采缺包件的实时项目(串行,每个 10-20s)。
- 找缺包件项目:`repack_missing()` 遍历 live 项目读 包件清单.json 包件数>0 判定。
- 实测:29 个实时项目缺包件清单,29/29 全部补采成功(公告搜索命中率:notTitle 按项目名前 20 字比翻页高得多)。

## 企业名归一化(数据池质量,用户问"为什么有简称有全称")
- 根因:实时采集企业名 = user/info 接口 dwhz 字段(**企业自填**,可简称"河南凡欧"/"嘉楠兴",甚至 "?" 空);官方库(供应商主数据 369K)= 工商全称。
- 归一化:去常见后缀(再生资源回收有限公司/环保科技有限公司/有限公司/公司...)→ 核心名 → 映射到官方全称。
- **性能铁律**:映射必须建成 dict 缓存(O(1)),**绝不能每个企业遍历 369K 文件**(listdir 每次=灾难);bot 侧缓存 5min,merger 侧模块级 _NAME_MAP 首次构建。
- 双层归一化:merger 合并 pack_map 时落盘归一化(防新简称混入)+ bot 展示层 norm_ent_name(兜底含匹配,如"嘉楠兴"→"重庆嘉楠兴再生资源回收有限公司")。
- 配套整理:账号去重合并(同账号多记录合并包件、按账号补全 "?" 名)、企业档案重建(全量 pack_map 聚合 → 企业档案目录,实时新企业也进档案)、index vs 文件夹一致性校验。
- 归一化脚本 pool_clean.py 可重复跑(幂等),4s 处理 6,220 个 pack_map。

## 服务器加固(反渗透防御,8 步)
1. 主服生成 ed25519 密钥 → 分发公钥到 5 台 authorized_keys → 测试密钥登录 → 再 `PasswordAuthentication no` + `PermitRootLogin prohibit-password` → 再上防火墙(顺序不能乱,否则锁死)。
2. 采集机 iptables:22 端口只允许主服 IP(ACCEPT)+ recent 限速(60s/6 次 DROP)+ 其余 DROP;主服 12971 同样 recent 限速。
3. 密码轮换(密钥已生效,密码仅兜底)+ jumpers.json chmod 600。
4. 入侵检测 daemon(security_watch.py):每 5min `lastb` 失败登录增量 → 超阈值 TG 告警;每日 sha256sum 关键脚本 vs 基线 → 篡改告警。
5. **坑:加固后本机直连采集机被防火墙 DROP** → 一切经主服跳板(主服私钥备份本机 .ssh/v6_master_key,paramiko pkey 认证)。
6. 云平台 SSH 爆破防护会临时封高频连接源 IP(表现 timed out)——先怀疑它,等待 60s+ 或经主服跳板确认。

## 其他
- 用户中心菜单扩容后 3 层按钮矩阵(18 个入口),/help 完整命令速查。
- /live 竞价实时面板(读 bid_status.json "竞价中" + bid_live.json)、/watch 企业监控(watch_ents.json,报名即推)、⭐收藏(stars.json 按 cid)、🕒浏览历史(browse_hist.json 按 cid 前 10)。
- 深链:`t.me/<bot>?start=proj_<pid>` → handle_text 解析 `/start proj_` 直达项目。
- 真 xlsx 零依赖:zipfile 手写 [Content_Types].xml + workbook.xml + sheet1.xml(inlineStr)。
- 功能使用说明文档:Desktop/*功能使用说明.md(12 章模板)。
