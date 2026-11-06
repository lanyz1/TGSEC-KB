# 登录线(priv):特权会话探测腿

定位:95306 采集体系里**与票池线(rail)并列的另一条腿**。票池线抓别人登录产生的票去补企业包件数据;
priv 线是**自己拿票换 ST 登录 → 拉菜单 → 打「高权接口矩阵」**,目标是竞价监控 / 包件核对 / 投标人列表这类高权端点。

## 组成(权威清单)

- **配置**:`conf/master.ini` 的 `[priv]` 段(其注释即写明「= 线上 priv_loop.py」),含
  `url_login = https://cg.95306.cn/proxy/portal/user/login`、`matrix_file = conf/priv_matrix.json`、
  `max_per_cycle = 80`(单轮最多验 80 票)、`sleep_min`(轮间隔)、`watch_cmd`(蓄水哨兵命令)、
  `watch_skip_types = 03,3`(**跳过企业类账号** —— 那是采集端的活)。
- **入口**:`python3 /opt/v6/v6m.py priv`(ROLE 映射到 `master.priv`)。**自带 while 循环的常驻进程**,
  由手工 `setsid nohup flock -n /tmp/v6_priv.lock …` 起,**不在 crontab 也不在 systemd timer 里** ⇒ 杀了不会自启。
  进程表上是三行:`bash -lc …` 壳 + `flock` + `python3 /opt/v6/v6m.py priv`。
- **两段式**:`master/priv.py` 的 `cycle()` 第一行 `harvest()`(= 蓄水,只负责 `subprocess.run(watch_cmd)` 催哨兵)
  → 再逐账号 `user/info` → 换 ST(`serviceTicket`) → `loadMenu` → `matrix()` 打端点矩阵。
- **蓄水哨兵**:`priv_tok_watch_v3.py`(线上老脚本,在 `/opt/v6/` 下,不在代码树里)。从 `tokenrailquery` 拉**登录流水**
  (`https://cg.95306.cn/proxy/dataplatform/api/findList`,窗口 = 最近 12×30 分钟、每窗 6 页 × 500),
  过滤 `login_status == "1"` **且** `user_type ∉ {03,3,""}` ⇒ 收进票簿;经中继 ssh 到采集机出网。
- **端点矩阵**:`conf/priv_matrix.json` —— 在**代码树里**(`current/conf/…`),`/opt/v6/conf/` 下没有;
  10 个端点(`bidMonitor_*` / `packCheckList` / `listBidderBy` / `reqPurchase_querySupplier` / `getProjInfo` …)。
- **产物与判读**:
  - `priv_tokens.json` —— 票簿(`userid` / `token` / `login_time` / `user_type` / `url`)
  - `priv_watch_seen.json` —— 哨兵去重表
  - `priv_probe_state.json` —— 逐账号探测状态(`alive` / `menu_n` / `auth` / `hits` / `resp` / `checked`)
  - **`priv_cov.json` —— 权威汇总**(`票据总数` / `命中票数` / `命中计数`)。判「这条线到底成过没有」**只看它**。
  - `priv_archive_<日期>/` —— 有人做过归档;归档前后都是 `{}` ⇒ 不是最近才坏的。
- **命中判据写死在 `matrix()` 的 bad 集合**里:`没有该功能的操作权限` / `未登录` / `系统服务异常` / `HTTP4*` / `HTTP5*`
  ⇒ 响应全落在里面时 `hits=0` 是**逻辑必然**,别当 bug 查。
- ⚠ `alive=True` **不等于票可用**:502/503 也会被记成 alive(它判的是「有没有拿到响应」)⇒ 看 `resp` 原文,不看 `alive`。

## 两层墙(先分开,别笼统写「这条线没用」)

1. **票新不新鲜**:看 `priv_tokens.json` 里 `login_time` 是否近期。旧票的响应形态 =
   `{"code":"100","success":false,"msg":"系统服务异常"}` / 401 / 502 / 503 ⇒ 一律 `bad`。
2. **有了票有没有权限**:即便拿到 `manage:user:default:…` 这种权限链(菜单 343 项,远超普通账号的 93),
   端点仍可能回 **`{"msg":"您没有该数据的访问权限，请联系技术支持！"}`** ⇒ 该链是**默认角色链,缺功能点授权**,
   只能靠平台侧配授权 ⇒ **外部拿不到**。
   ⇒ 恢复票源只能把「票死」与「无权限」**分离**;若活票仍全被拒,结论就是这条线**该正式关停**。

## 已修过一次的「断奶」bug(同类现场照此处对照)

哨兵连续多周报 `ROWS 0 wins_with_rows [] NEWTOK 0`,而独立探针同参数拿到满页行:
`priv_tok_watch_v3.py` 里**调用点是 `post(FL, {...})`,定义已改名为 `_relay_post(data, tmo=60)`** ⇒ `NameError`;
只改名还不够 —— **多传一个实参**会把那个 dict 顶进 `tmo` ⇒ `subprocess.run(timeout={...})` 抛 `TypeError`。
两者都被外层 `try/except: break`(**无日志**)静默吞掉 ⇒ 观测面只剩 `ROWS 0`,
整条腿因此空转(from 脚本 mtime 那天起;票簿最后一张新票与之吻合)。
**修法 = 加兼容包装**(`def post(url, data): return _relay_post(data)`)⇒ 副本上实测立刻恢复取数(3 窗 2881 行)。
副本 + 单变量 + 缩规模 + 进度行的验证形态见 `remote-exec-script-harness` §6。

## 停机 / 回滚

```bash
# 停
pkill -f "v6m.py priv"
ps aux | grep "v6m.py priv" | grep -v grep || echo STOPPED_OK
# 起(原样回滚)
cd /opt/v6 && setsid nohup flock -n /tmp/v6_priv.lock python3 /opt/v6/v6m.py priv >> /tmp/priv_loop.log 2>&1 &
```
- 停之前先留档 PID + `lstart` + 原启动命令,报告里带上回滚命令(用户要求一切改动可回滚)。
- **零产出的腿要算风控账**:它每 8 分钟用 80 张票打 `/user/info`,出口是采集机 IP —— 而 `/user/info` 正是采集线
  风控冷却的触发点。平台冷却键是账号级/票级(`cool_acct`/`cool_st`),两条腿不共享计数,但同一出口 IP 上长期堆
  401/100 会抬高 IP 级异常画像 ⇒ **连续多周零产出时,先停线再谈修复**。

## 判读纪律

- 说「抓不到新票」之前**必须先实测票源**:一发探针 = 窗口查询 + 统计 `login_status` / `user_type` 分布 + 最新 `login_time`。
  实测结论可能与「平台没数据」相反:平台侧货一直很足(90% 登录成功、合格新票数百张、最新票在 3 分钟内)。
- **用户凭记忆说的「之前是正常用的」当作真线索**:按回归 bug 查(最后有产出的时间点 + 脚本 mtime + 归档时间戳三者对齐),
  不要答「平台策略变了」;实测中正是这条线索指向了改名漏改调用点。
- 报告里区分「跑得动但零产出」与「跑不动」:前者的证据链是 `priv_cov.json` + `resp` 原文 + 票龄,不是日志行数。
