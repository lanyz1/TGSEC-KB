# v9.18 `/q` 状态口径统一到 stage(2026-09-10)

## 背景/定论
- 旧:`/q` 状态筛选用平台 status 码(14=结果发布后才"已结束";19/13 长期挂着不更新)→ 刚结束的项目搜不到,还残留一堆"已结束却挂 19/13"的虚高。
- 新(v9.18,用户批准"顺便也做"):`/q` 状态 = **stage 口径,与 🏁 菜单同源**;等级:**竞价室关闭即"已结束"**,不再等平台 status=14。

## 代码
- `pix_bot_server.py` 的 `match_query`(约 L2998,**唯一状态过滤点**;run_query / query_matched / _do_qrydl 全走它):
  - 进行中 → `stg in ("报名中","待竞价","竞价中")`
  - 已结束 → `stg == "已结束"`
  - 竞价中 → `stg == "竞价中"`
  - 未开始 → `stg in ("报名中","待竞价")`
- stage 取值:报名中/待竞价/竞价中/已结束/**历史**(merger `_stage_of` 计算;index.json 每项目带 stage 字段)。实测总 21924 项目:已结束21534 / 待竞价124 / 报名中149 / 竞价中2 / 历史115。

## 线上前后对比(index.json,2026-09-10)
- 已结束 20719 → **21534(+815 补齐)**;进行中 484 → 275(剔 221 个"已结束仍挂19/13");竞价中 66 → 2;未开始 418 → 273。
- 新补样本(status≠14 但 stage=已结束):广西沿海17次废钢铁 / 天佑京铁2次废电子电器 / 郑州局2次报废汽车 / 沈铁82次废钢轨 / 南宁局60次废钢轨…;当天刚结束的 6 个也即时可查。

## 部署实证(备份→上传→kill→start 全分离)
- 双端 md5:旧 `fd9edc01` → 新 `7d478018`;备份 `/opt/v6/pix_bot_server.py.bak_v918pre`(回滚=覆盖回去+重启)。
- 流程:本地 patch → py_compile → sftp put /tmp → master 上 py_compile + md5 双验 → 覆盖 → 再验 md5。
- **kill 用显式 PID**:FIND=`ps -eo pid,cmd | awk '/python3 pix_bot_server.py/ && !/awk/ {print $1}'` → 单独 exec `kill <pid>` → 轮询确认清空后才行。
- **start 单独 exec**:`cd /opt/v6 && setsid nohup python3 pix_bot_server.py >> /opt/v6/pixbot.log 2>&1 & echo UP`。
- ⚠️ **paramiko 读超时假象**:start 那条 exec 的 read 会 PipeTimeout(120s,后台进程持住通道)但命令**已执行**;别重发(重发=双实例),另开连接用 `ps -eo pid,lstart,cmd` 验证(新时间戳 + 单实例)。
- ⚠️ 计数自匹配:`ps -eo cmd | grep -cF '...'` 把 bash -c 自身和 grep 也算进去(显示 4=实际 2);看 `grep -F ... | grep -v grep` 明细行。
- TG:kill 后等 ~5s 再 start(长轮询释放,防 getUpdates 409);实测停机 ~10s。
- 运行日志 `/opt/v6/pixbot.log`(启动三行:启动[数据池]/[启动]/[定时]);bot 无 systemd 守护。

## 验证方法(无需 E2E,别 import 整个 bot)
- import bot 会启动 polling → 与线上实例 409。改用**提取函数段 exec**:
  `code = src[src.index("def match_query"):src.index("def run_query")]`;`ns = {"datetime": datetime}` ← 注意注入的是**类**(bot 顶部 `from datetime import datetime`,给模块会报 `module has no attribute 'now'`)。
- 跑真实 `/data_pool/index.json` 统计四口径;再参数化对照:`old = count(status=="14")` vs `new = mq(...,{'status':'已结束'})`,输出 delta + 补入样本清单(证明效果)。

## 遗留(本次未动,待用户定)
- 分类总览「按状态」是独立旧体系(live→bid_status.json;历史→status 码 14/22/else;带「流标」桶)→ 统一需先定"流标"桶归并规则。
- `/q` 日期过滤用 `datetime.now()`(master UTC)比北京时间串,凌晨窗口有 8h 边界伪影(白天无感)。
