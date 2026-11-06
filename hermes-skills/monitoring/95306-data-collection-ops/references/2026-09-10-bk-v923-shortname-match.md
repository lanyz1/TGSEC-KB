# 2026-09-10 点名漏采企业定位 + v9.23 简名匹配修复(bk_worker)

## 结论(锤死):bk 漏采根因之一 = 名册全名 ≠ 平台显示名(dwhz)

- 用户点名 23 家"反复漏采(4-5次)"企业(河南崇锐/乌鲁木齐欣和庆/张掖荣华/郑州硕丰/西安融旺/南京东创/南京中亚等)逐一全库定位:
  - 23 家全部在漏采集(ctx miss_names);全池 `backfill8` 回写 741+ 家、按日 90~395 条、当日 10:03 仍在出单 → **通道活着,问题特定于这批**;23 家 backfill8 命中 = **0**。
  - 登录流直查:实测 7 家出现在 tokenrailquery(全为 供应商/03/status=1,bk 本应扫到);username=简名/账号(xajw001/shuofeng/njdc123456/信达环宇/西安融旺…)。
  - 铁证(观察哨 9/10 17:26 河源):`uid=shuofeng dwhz=郑州硕丰 比对=DIFF` + 同 token `getBuyPackageList` 拉回 **20+18 个包件** → **数据随时可得,卡在"名字比对"**。
- 机制:命中判据原为 `norm(dwhz) == 名册全名` 整串相等;简名账号永远不命中 → 永久漏采。
- 与既有结论的关系(互补,不重叠):见 references/2026-09-11-username-scan-final-verdict.md 的"SSO 长会话零事件"类——那类=报名期无认证事件可抓;本类=**有登录事件但被匹配挡住**,v9.23 解锁。

## 修复 v9.23(bk_worker.py)

- 唯一改动点 = `jv.get("code") is None and jv.get("success")` 匹配分支;`miss_items` 索引加在 miss_norm 定义后:
  1. 全名 norm 相等 → 命中(原逻辑);
  2. 否则若 `len(norm(dwhz))>=4` 且**唯一**是某名册全名的子串 → 命中,打 `SUBHIT` 日志;
  3. 多命中 → 放弃(防误配)。
- 部署:md5 1677c650→7ecacc43,备份 bak_v923pre;文件替换即生效(orch 每轮把 /opt/v6/bk_worker.py 下发 12 台),无需重启;验证看机器 /tmp/bk8_N.log 的 SUBHIT/HIT 与主服 orch 日志 `企业N 项目写入N`。
- 教训:字面量/子串匹配**必须验证或加唯一性约束**(实测误报:云南顺安≠成都顺安永达;赵荣法≠郑州荣法)。

## 漏采企业定位工具箱(本次新建,可复用)

1. **名册diff**:`plat_enroll_map[projCode]["企业"]` vs `/data_pool/<pid>/pack_map.json` 单位 → per 企业采/漏统计(脚本 Temp/q3_companies.py)。
2. **登录流直查**:findList `funcId=tokenrailquery`;**username 字段带显示名**(全称/简名/账号码);粗筛=全名/简名/手机号(供应商档案 369k 份含手机号)字面量 → 命中后 user/info 解析 dwhz 细验(Temp/q4_diag.py / q8_probe.py)。
3. **通道产出审计**:`grep -rlF backfill8 /data_pool --include=pack_map.json` → 条目按日/企业统计(判通道死活、判某企业是否曾被回写;条目"时间"=登录时间,非写入时间)。
4. **数据水位探测**:从 now-30min 逐 30min 窗回搜,**最新非空窗=水位**;水位旧于 6h → bk 扫 [now-6h..now] 整轮空转(9/10 实测断供 10:10→17:25 后自愈;~7-9h 旧 token 仍 61/260=23% 可解析)。脚本 Temp/q12_probe.py。
5. **观察哨模式**:采集机 setsid nohup 后台,循环[找水位→扫 [W-90m,W]→字面量命中→当场 user/info + getBuyPackageList 实测→写日志],限时自动退出。脚本 Temp/q13_watcher.py(日志 /tmp/q13_watch*.log)。

## 判据/坑

- `user/info` 对 失效/冷却/垃圾/无鉴权 token **同回 `code=100 系统服务异常`**——无法区分,勿据此判死;真实有效=code None + success。
- 平台登录流有 **hours 级断供/水位**现象;bk 固定窗遇之即空转,长期方案=按水位移动扫描带(待做)。
- 抓取 URL:`/business-proxy/business/user/info`(Authorization=token);`/business-proxy/business/supplierPackage/getBuyPackageList?projId=`。
- 02 集团公司占登录量 ~38%(9/10:4156/11116),bk 只扫 03,是否另一结构盲区待评。
- 陕西晨易阳商贸有限公司:名册/CSV/登录流/档案全零痕迹(最深盲区样本,单独盯)。
- 探针执行:本地→主服(key=~/.ssh/v6_master_key)→采集机(jumpers.json 密码)两级 paramiko;文件 base64 推 /tmp;setsid nohup 启动读超时=假象,新连接 ps 验证。证据脚本全套在 Temp:q3/q4/q5/q8/q11/q12/q13。
