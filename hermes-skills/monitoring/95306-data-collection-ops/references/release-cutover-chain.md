# 发布树 → 割接 → 上线：定序、判据与本地假红

## 定序（缺一步就报错，不是可选项）
1. `python deploy/build_release.py` ⇒ `dist/v6rel_<stamp>.tar.gz` + `manifest_<stamp>.json`。
2. `scp` 两件到主控 `/opt/v6/dist/`，**两侧 `sha256sum` 对一遍**再往下走。
3. **`--stage` 必须先做**：`python3 <树>/deploy/master_deploy.py --stage --rel <rel> --tar <tar>` ⇒ 解包到 `/opt/v6/lib/<rel>`。不做它，`--verify` 直接报「树不存在」。
4. `--verify`：树在 + `IMPORT_OK` + launcher 可执行。
5. `--plan`（只读）：输出 `unknown / bad_block / problems / new_entries_src / prev_block_lines / running_old / verdict`。
6. **`--activate --yes` + 常驻 bot 重启 = 生产闸**：停下等用户点头。kill 与 start 分两次 exec、核残留 0、`flock -n /tmp/v6_bot.lock` 释放、双 bot 不同跑；用户没说要就不放上线公告。

## 判据读法
- **配置来自「被调用脚本自己那棵树」**：`--plan` 打印的 `cutover <路径>` 就是它实际读的那份。验证**新树**配置要用 `lib/<rel>/deploy/…` 跑；用 `current/deploy/…` 跑验证的是**旧树**那份 —— 两者不可互相背书。
- `verdict 可割接` 的前提是 `unknown` 与 `bad_block` 都空、`problems` 空。
- `prev_block_lines` = 上一版受管块被识别到的行数；它掉到 0 就是块内行没被认出来（本地假红的第一表现）。

## 会让 `--plan` 判「★拒绝割接」的雷
- **新加的手工 cron 行未归类**：线上有、既不在受管块、也不匹配模板的行被记成 `unknown` ⇒ 当场拒。修法：把脚本名加进 `deploy/master_cutover.json` 的 `keep_scripts`（保留清单按**脚本名子串**匹配，语义＝线上原行逐字保留）。
- 反向坑：把**该受管的**行塞进 `keep_scripts` ⇒ 它逃出割接管理、升级后仍跑旧入口。受管角色一律走 `new_entries`，只有树外手工脚本进 `keep_scripts`。
- 改过 `deploy/` 或 `tools/` 里任何文件 ⇒ **重打树**再 stage/verify/plan（树按整目录打包，旧测试/旧配置会被一起带上线）。

## 本地（Windows/MSYS）跑闸的假红三族
1. **路径分隔符**：`os.path.join("/opt/v6","v6m.py")` 出 `\` ⇒ `LAUNCHER in 行` 永不命中 ⇒ 受管块识别 0 行、多行误判 `unknown`、连锁红一片，而**真机 Linux 本来就是绿的**。⇒ 只在**比较前**把 `\` 归一成 `/`（真机空操作，断言严格性不放松），不要改生产侧拼接。
2. **行尾**：夹具快照被 Windows 写成 CRLF ⇒ `read` + `split("\n")` 的行尾带 `\r` ⇒ 块标记/模板比对失配。读夹具一律 `rstrip("\r")`。
3. **`PYTHONPATH` 分隔符**：Windows 用 `;`；`PYTHONPATH=.:deploy` 会被当成**一个**条目 ⇒ `ModuleNotFoundError` 看着像代码坏、其实是跑法。固定 `export PYTHONPATH="D:/<树>;D:/<树>/deploy"`。

## 闸的权威性排序（别把噪音红当真回归，也别把真红当噪音）
- **`deploy/verify_release.py` 是发布判据**（②compileall ③模块导入 ④自测桩 run/cli/master/bot/bk ⑤落盘纪律 ⑥指纹+tree_hash ⑦结构+绑定 ⑧TZ=UTC ⑨割接机制）；它打「上线判定：可以上」才允许上。
- `tools/offline_*.py`、`tools/test_*_offline.py` 是**附加**件，不在发布闸名单内；但红着会污染判读（曾有把真契约问题误判成「测试陈旧」的险情）⇒ 优先修绿。
- 断言把常量写死、生产侧又重构过 ⇒ **按真实契约重新点名**（保持严格），不要删断言、不要放宽成恒真。
- 跑法差异：`offline_groups`/`offline_state_cases` 需 `PYTHONPATH=.`；`test_deploy_crontab_offline` 需把 `deploy` 也放进 `PYTHONPATH`（`master_deploy_parts` 是 deploy 目录内的裸名导入）。
- 手跑闸批量件放 scratch 写 `gate_all*.sh`（含 `export PYTHONPATH`），每个闸打尾部 3–4 行 + 退出码，别在一行里塞十几个闸（长内联命令会被拦）。
