# SFTP 增量同步陷阱与 tar 全量根治 — 95306 v6 实录(2026-09)

## 症状

- 8/31 平台发布 46 个新公告,数据池只收录 2 个(用户人工核验发现)。
- 排查链:公告接口打通(需 business-proxy 前缀)→ 46 个 projId 对比 index.json → 采集机 `/tmp/targets/` 数据全(268 项目 × 5 文件,含缺失的 c840e058)→ 主服 `/data_raw/上海/` 只有 426 个扁平文件且无 c840e058 → **问题锁定在主服 merger 的 rsync 拉取环节**。

## 根因(两层叠加)

### 坑 1:mtime 跳过判断永远不成立

```python
# merger.py 原逻辑
if os.path.exists(df) and abs(os.path.getmtime(df) - f.st_mtime) < 2:
    continue  # 相同跳过
```

- paramiko `sftp.get()` **不保留远程 mtime**,本地 mtime = 下载时刻。
- 实测:远程 mtime=1788207396,本地=1788207599,**差 203 秒** → 跳过条件永假 → **每轮重复拉同一批文件**。
- 只修这里不够(坑 2)。

### 坑 2:"从头遍历 + 时间预算截断"无游标死锁

```python
files = sftp.listdir("/tmp/targets")   # 268 个目录,顺序不稳定
for pid in files:
    if time.time() - t0 > 110:         # 预算
        break                          # 每轮从头开始!
    ...
```

- 110 秒预算只够处理 ~24 个目录(listdir_attr + 5×sftp.get 每个目录 2-3 秒)。
- 每轮从列表头开始 → **列表后面的项目永远轮不到**。
- 即便修好 mtime,遍历已处理目录的 listdir_attr 开销照样烧光预算,推进不了。

## 根治:tar 全量打包同步(不要修 mtime)

```python
# pull_one 内(每台采集机,4 台并行):
c.exec_command("cd /tmp/targets && tar czf /tmp/targets_all.tar.gz .", timeout=90)
# 轮询等待 tar 完成(读 err.channel.recv 直到 ls -la 输出出现大小)
sftp.get("/tmp/targets_all.tar.gz", f"/tmp/v6_tar_{name}.tar.gz")
with tarfile.open(local_tar, "r:gz") as tf:
    tf.extractall(tmpd)                 # /tmp/v6_unpack_<name>/
# 扁平化:
for pid in os.listdir(tmpd):
    p = os.path.join(tmpd, pid)
    if os.path.isdir(p):
        for fname in os.listdir(p):
            shutil.move(os.path.join(p, fname), os.path.join(dest, f"{pid}_{fname}"))
    else:
        shutil.move(p, os.path.join(dest, pid))   # 根级 json 直接放
```

- 实测:4 台 × 1100-1800 文件 = **6-8 秒/台**,全量幂等,无任何增量判断。
- 心跳文件 `/tmp/v6_heartbeat.json` 仍单独 sftp.get。
- 验证:`ls /data_raw/上海/ | grep -c <projId前8位>` + index.json 收录数对比公告清单。
- 效果:8/31 公告收录 2/46 → 39/46;index 21,219 → 21,589;合并项目 130 → 668。

## 同类"已有则跳过"检查清单(增量跳过导致数据过期)

排查数据缺失时逐项问:

1. **跳过判断依赖 mtime/SFTP 属性?** → sftp.get 后必须 `os.utime(df, (f.st_mtime, f.st_mtime))` 对齐,或干脆全量。
2. **列表遍历无游标、预算截断?** → "从头开始 + break"模式,尾部永远轮不到。
3. **内容型跳过**(如采集机 `if d.get("包件数", 0) > 0: continue`)?→ 源数据更新(二次挂网/公告修改)后永不重拉 → 需比对公告标题/id/状态变化强制重拉(标题含"二次/2次/(2)"风险最高)。
4. **发现源固定过滤条件**(如 `selectSelfSellList` 固定 `bidType=02 + status 13/19/22`)?→ 询价/单一来源/谈判/线下类公告**结构性盲区**,永远进不了管道(8/31 剩 7 个缺失全属此类)→ 需公告流发现源(`queryBusinessNoticeList` 按 pubTime 增量)兜底。

## 部署脚本路径坑(Windows 本机)

- 本机 Windows Python 里 `sftp.put("/mnt/c/Users/...", ...)` **静默失败**(MSYS 路径只在 bash 有效)。
- 部署脚本必须写 `C:/Users/...` 格式。
- **部署后 grep 关键函数名验证**(如 `grep -c 'tar 全量' /opt/v6/merger.py`),不能只看 exit 0 / DEPLOY_OK——put 失败抛异常时,后续 exec_command 可能根本未执行,但连接/编译步骤仍会打成功标记。
- 第一次部署失败表现:字节数未变(40737→40737)、grep -c 0,但脚本输出 DEPLOY_OK。教训:验证输出必须含 grep 结果,不能只看 echo。

## 时间线速记

- 403 根因(前一轮):公告接口必须走 `/business-proxy/business/...` 前缀(Spring Security 网关自动附加 CSRF),裸 `/notice/...` 缺 CSRF 被 403;采集机 bfwz_post 已带前缀无此问题。
- ES 索引滞后(8/28 止)不能作核验来源;公告列表接口 `queryBusinessNoticeList` 21,091 条,8/31 过滤字段=`pubTime`(非 checkTime)。
- 8/31 缺失 7 类:询价(郑州物资 10/11 次)、单一来源(兰州通信段 ×2)、线下(兰州通信段)、谈判(乌局旅游)、特殊销售(银川车站竞销 002)、中铁快运成都。
