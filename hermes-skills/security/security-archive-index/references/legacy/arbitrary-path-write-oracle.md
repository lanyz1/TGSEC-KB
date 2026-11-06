<!-- archived from /root/.hermes/skills/security/arbitrary-path-write-oracle/SKILL.md on 2026-10-21 -->

---
name: arbitrary-path-write-oracle
description: "触发: 任意路径写/磁盘oracle/pprof/heapdump路径。内容不可控写→文件系统测绘+RCE天花板判定。"
version: 1.0.0
metadata:
  hermes:
    tags: [pentest, arbitrary-write, debug-endpoint, geth, heapdump, disk-oracle, cwe-73]
    related_skills: [rpc-txpool-mev, arbitrary-write-to-rce, file-upload-webshell, server-getshell-playbook, lowcode-admin-rce-primitives]
---

> 归档卡：原目录 `/root/.hermes/skills/security/arbitrary-path-write-oracle`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/arbitrary-path-write-oracle/…')`，不要相对 `references/legacy/` 解析。

# 任意路径写原语的磁盘 oracle 家族（内容不可控也算）

**与 `arbitrary-write-to-rce` 的分工（很重要，混用会把天花板判错）**：
- `arbitrary-write-to-rce` = **内存**任意值写（堆/格式化字符串/OOB）→ GOT/hook/ROP
- **本卡** = **磁盘**任意路径写、**内容不可控**（服务端自己造的内容，你只能定路径）

## 何时用

- 某接口/调试面接受**服务器路径参数**并落盘（profile / heapdump / 导出 / 备份 / 日志 / 解压 / 缓存目录）
- 已经能往服务器"写点东西"，但**读不回、内容也改不了**
- 要回答三个问题：**能不能变 RCE / 能破坏什么 / 能不能恢复**

## 1. 产地家族（路径参数 = 写原语）

| 产品/面 | 接口 | 路径可控性 | 内容可控性 |
|---|---|---|---|
| 自建链节点(Geth/BSC) | `debug_writeMemProfile` / `writeBlockProfile` / `writeMutexProfile` / `cpuProfile(file,sec)` | 完全可控 | 固定 pprof |
| 自建链节点 | `debug_standardTraceBlockToFile` | 不可控(写 datadir/`/tmp`) | 固定 trace |
| Java | `/actuator/heapdump`(路径不可控)、`jmap -dump:file=<p>`、`-XX:HeapDumpPath=<p>` | 部分可控 | 固定 hprof |
| Node.js | `--cpu-prof --cpu-prof-dir=<p>`、`--heap-prof-dir=<p>`、inspector `HeapProfiler.takeHeapSnapshot` | 可控 | 固定 profile |
| .NET | `dotnet-dump collect -o <p>`、`DOTNET_DbgMiniDumpName` | 可控 | 固定 dump |
| 通用运维面 | 导出/备份/报表/日志 的 `path` `file` `filename` `dir` `out` `dest` 参数；解压 `-d`；缓存目录 | 常部分可控 | 应用数据或固定包 |
| 云/容器 | OSS/S3 同步本地根、挂载卷路径 | 可控 | **内容可控 ⇒ 直接 RCE** |

**分类第一步**：内容可控 → 直接走 `server-getshell-playbook` / `cms-updater-zip-extract-rce`；
内容不可控 → 留本卡（只能 oracle + 破坏 + 等触发）。

## 2. 五态差分 oracle

先拿"已知不存的路径 / 已知目录 / 已知无权限路径"标定基线，之后每条响应都带信息量。

| 状态 | Geth 原文 | 通用映射 |
|---|---|---|
| **可写** | `{"result":null}` | 返回成功 / 200 且无报错 |
| 目录 | `is a directory` | EISDIR / 目标为文件夹 |
| socket/设备 | `no such device or address` | ENXIO / 非普通文件 |
| 无权限 | `permission denied` | EACCES（**权限边界**） |
| 父目录不存在 | `no such file or directory` | ENOENT（目录树不存在） |
| 只读文件系统 | `read-only file system` | EROFS（容器/挂载） |
| 其它 | 逐字记录原文 | 不可归类就不归类 |

**每次请求 = 1 bit**。扫一遍路径清单就能画出：运行身份与 HOME、datadir、
配置文件、启动/部署脚本、`.bashrc`/`.profile`、keystore 目录、IPC socket，
以及**被拒目录**（站根、`/etc/nginx`、`/etc/cron.d`、`/root`）——后者直接给出"任意写能不能变 RCE"的判决。

可直接复用的扫路径清单：`rpc-txpool-mev/references/geth-debug-arsenal.md` 第 4 节（含六组分级路径）。

## 3. 工具

```bash
python3 scripts/fs_oracle_scan.py --selftest                  # 先离线自证分类逻辑
python3 scripts/fs_oracle_scan.py \
  --rpc https://rpc.example/eth \
  --method debug_writeMemProfile \
  --paths paths.txt --delay 0.4 --out result.json
```

**纪律**：串行 + 限速（默认 "0.4s/请求"）；路径表不得含 keystore/私钥类目标。

## 4. 覆写靶标矩阵 → RCE 判定

| 靶标类 | 触发条件 | 能 RCE 吗 |
|---|---|---|
| 服务配置/密钥（`config.toml` `jwtsecret` `nodekey` `password.txt` `genesis.json`） | 重启或重载配置 | 否（**自毁型**，服务失联） |
| 用户级 shell 配置（`~/.bashrc` `~/.profile`） | 等运维/管理员**下次登录** | **是（等触发）** |
| `authorized_keys` / `crontab` / `cron.d` / systemd unit / `~/.ssh/config` | 定时或下次连接 | **是（等触发）**，但常 `permission denied` |
| web 站根 / 反代目录 / `application.yml` | 直接请求 / 重启应用 | **是**，但常被权限挡住 |
| `keystore/` / 私钥 / 证书 | 立即不可逆损坏 | **否；且禁止**（资产永久锁死） |
| `/tmp` `/dev/shm` | 需另一条链（日志包含/文件包含）配合 | 否 |

**RCE 三要素：能写 → 内容能影响执行 → 有触发点。缺一就诚实写"任意路径覆写(内容不可控)、未达成 RCE"。**
别把"写成功"当 getshell（用户会纠正）。

## 5. 纪律：破坏性与可恢复性

- 动手前先答"**能不能恢复**"：覆写 = **不可逆**（Geth 案已把 `jwtsecret`/`nodekey`/`config.toml`/`password.txt`/`genesis.json` 写成 pprof）
- 验证写点只挑 `/tmp` `/dev/shm` 或明确可重建的文件；扫目录取 `is a directory` 不产生副作用
- `keystore/*`、私钥、证书、数据库文件：**只判存在性，绝不写**
- 报告里必须有这句："路径可写 ≠ 原文件内容可读"（这是这类漏洞最大的误报源）

## 6. Pitfalls

1. **写成功 ≠ 能读**。只有写原语时，最多只能说"该路径可被覆写/新建"；不得推"服务器上存有明文秘钥"。
2. **目录存在 ≠ 目录内容可读**。`is a directory` 只证存在。
3. **同一路径两次结果不一致** → 先怀疑反代后面多个后端（负载均衡），不是"并发竞争"。
4. **内容不可控 ≠ 没价值**：文件系统测绘 + 节点自毁/服务失联本身就是 P0 级影响，别因为"不能 RCE"就不报。
5. **`/proc/self/exe` 返回 `text file busy`** 不是写成功；`/proc/self/cmdline` 常 `permission denied`；这两条是区分"写"与"读"原语的好素材。
6. **多主机隔离先判定**：写 `/home/A/` 报 `no such file`、写 `/home/B/` 报 `permission denied` ⇒ 两台机或强隔离容器，别按同一台推横向。
7. **别拿"疑似存有助记词"当发现**：路径叫 `mnemonic.txt` 只能说明有人起过这个名，写成功不证明内容。

## 7. 关联

- `rpc-txpool-mev` — Geth/BSC debug 实战（方法矩阵 + 扫路径清单 + 真实案例）
- `arbitrary-write-to-rce` — 内存任意值写（不是本卡）
- `server-getshell-playbook` / `cms-updater-zip-extract-rce` / `file-upload-webshell` — 内容可控时的 RCE 路径
- `lowcode-admin-rce-primitives` — 后台文件写/执行原语体检
