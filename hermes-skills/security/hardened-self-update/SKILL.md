---
name: hardened-self-update
description: "给工具、agent 平台、单二进制服务做自升级通道时加载：更新源写死与域名白名单（Repo、latestURL、allowedHosts）、逐跳重定向校验、SHA256SUMS 拉取比对、版本单调性与 prerelease/draft 过滤、stage 目录加原子 rename 换装、尝试计数回滚、bootstrap 首装校验点；要防换包、防 DNS 污染、防更新源被改成 RCE、要写校验与回滚时用这张卡。触发词：自升级、自更新、换包、替换安装包、回滚。"
sources: art-content, operator_experience
---

# hardened-self-update

## 定位

把「一键升级」压成一条窄管道：HTTPS + 五个域名白名单 + 一份 SHA256SUMS + 一次冒烟 + 三次启动确认，缺一环就继续跑旧版。

## 威胁模型

- **更新源可配 = 任意代码执行通道**。配置里能改 owner/repo 或 base URL，改配置的人就让平台在下次升级时拉下自己的二进制，并以平台自身权限执行。平台跑在运维机或服务器上，这条通道等价 root。
- **DNS 污染 / 中间人**：把 api.github.com 或资产域名解析到自控 IP，回一份 tag 齐备的 Release JSON。
- **镜像 / release 资产劫持**：在 CI 侧替换 zip 或 SHA256SUMS，做到「校验通过，装的是别人的二进制」。
- **降级攻击**：latest 指向低版本，或拿新 tag 装旧内容，让平台自降而不报警。

## 源固定与域名白名单

- `Repo` 写死成 `"<owner>/<repo>"` 字符串常量，`latestURL = "https://api.github.com/repos/" + Repo + "/releases/latest"` 一起写死：不进配置文件、不进 Web UI、不读环境变量。理由：更新源一旦可配，那份常落在二进制同目录、还会被备份脚本带走的配置文件就是提权入口。唯一交出去的自由度是出口代理（`proxy` 可选参数，只改出口 IP，不改 URL 结构）。
- `allowedHosts` 只放 5 个：`api.github.com`、`github.com`、`objects.githubusercontent.com`、`release-assets.githubusercontent.com`、`raw.githubusercontent.com`。后三个是 release 资产与 raw 内容的真实落地点，少一个下载就断，多一个就是白送一跳。
- `checkURL` 三条判定：scheme 必须是 `https`；取 `u.Hostname()` 转小写后查表（不带端口、不带 userinfo，`github.com.evil.com` 这类后缀伪装与大小写变形一起挡）；每个请求发出前都调一次，`fetchSums` / `get` / `FetchLatest` 三处都过这道闸。

## 传输层校验

- 独立 `http.Transport`：`ForceAttemptHTTP2` + `TLSHandshakeTimeout 15s`，刻意不复用全局默认 Transport（全局那份被别处塞进 `InsecureSkipVerify` 时照样跳验）。
- `Client.Timeout 30m`（整包下载，不按请求级卡死）；`CheckRedirect` 里 `len(via) >= 10` 直接失败，其余每跳 `checkURL` 复检 —— 重定向到 `http://` 或名单外主机当场中止，不留「先跟随再验」的窗口。
- 响应大小上限：SHA256SUMS 用 `io.LimitReader(body, 1<<20)` 卡 1 MiB；解压二进制用 `io.LimitReader(rc, maxBinarySize+1)` 卡 512 MiB（`maxBinarySize = 512 << 20`），超限拒收。
- 字节数核对：`asset.Size > 0` 时写入字节数必须与 Content-Length 相等，短读判「下载不完整」。
- 状态码分流：403/429 → 未认证 GitHub API 限流 60 次/IP/小时；404 → 该 repo 没有正式版；其余非 200 直接失败，不拿错误页当资产。

## 完整性

`Stage` 内固定六步，跳步即拒：

1. 由 tag 拼资产名 `<name>-<去 v 版本>-<GOOS>-<GOARCH>.zip`，`FindAsset` 用 `EqualFold` 匹配；缺本平台包即失败。
2. 先拉 `SHA256SUMS`（常量 `sumsAsset`）。Release 里没有这份清单 → 拒绝升级，不是「跳过校验继续装」。
3. `parseSums` 只收「恰好两个字段 + 首字段严格 64 位 hex」的行，剥掉 shasum 二进制模式的 `*` 前缀，摘要统一小写；空行、说明文字、`deadbeef` 这类短摘要全部丢弃。摘要表里查不到本平台包名 → 拒绝安装。
4. 边下边算：`io.MultiWriter(file, sha256, progressWriter)`，落盘后 `f.Sync()`。
5. `EqualFold(实际, 期望)` 不等即失败，报错只露前 12 位摘要。
6. 解压 → `smokeTest` → 再算一次二进制自身 sha256 写进 `<exe>.new.sha256`，供下次启动做二次校验。

签名层照实记：这条链只有 SHA256SUMS 一层摘要信任，清单本身靠 TLS + 域名白名单保护，没有 cosign / minisign 独立签名密钥，信任根上限就在这里。

版本单调性：`CompareVersions` 只认纯三段式 `v?X.Y.Z`；`parseVersion` 对 `dev`、`0.3.7-2-gabc1234`、`0.3.7-dirty`、`0.3` 一律 `ok=false`，调用方据此禁用一键更新，挡住「开发构建被正式版覆盖」。prerelease/draft 不在客户端判，直接吃 `/releases/latest` 的语义。

## 落地与替换

- 路径全挂 `os.Executable()` 所在目录（先 `EvalSymlinks` 再取 `Dir`），不用 CWD：服务化运行时 CWD 落在 `/` 这类位置，暂存件跟着跑偏就换不了装。命名对称：`Current=<exe>`、`New=<stem>.new[.exe]`、`Sum=<New>.sha256`、`Old=<stem>.old[.exe]`、`Marker=<stem>.upgrade.json`。
- 写前探可写：`os.CreateTemp(dir, ".probe-*")` 成功后删掉，避免下完几十 MB 才在换装那步失败。
- 临时件同目录：`<New>.zip.part`、`<New>.part`，`defer` 清理，保证最终 rename 在同一文件系统内原子完成。
- 换装 `swap()`：先删旧 `.old`（Windows rename 不覆盖已存在目标）→ `Current→Old` → `New→Current`；第二步失败必须把 `Old` 原样 rename 回 `Current`，否则下次启动没有可执行文件。
- 进程占用：Unix 与 Windows 都允许 rename 正在运行的可执行文件，所以不停进程、不删自身；重启靠退出码 `ExitRestart = 75`（EX_TEMPFAIL），守护脚本见 75 立刻重跑、见 0 退出循环、其余按崩溃退避。
- 权限与属主：解压时 `OpenFile(..., 0o755)`，冒烟前再 `chmod 0o755` 兜一次；文件属主继承安装用户，不动 ACL。
- 回滚：`marker{from,to,attempts,staged_at}`，`maxAttempts = 3`；换装后每次启动 `Attempts++`，超过 3 次仍未过 `SettleDelay`（30s，HTTP 监听起来后延迟调 `Settle` 删 marker）→ `rollback()`：`Current→Current.failed` 留证不删 → `Old→Current` → 删 marker → 再 `exit 75`。手滚 `Rollback()` 走三方 rename（`Current→.swap`、`Old→Current`、`.swap→Old`），滚完还能滚回来，且滚前先 `smokeTest(Old)`。

## 引导式首装

`install.sh` 是首次落地的信任起点，校验点只有三处，其余等于相信源头：

- docker 缺失时 `curl -fsSL https://get.docker.com | sh` 管道直执行，无摘要、无签名，整条链上最软的一环。
- `docker compose pull` 不落盘镜像 digest，`up -d` 之后只靠 tag 指向；脚本里写成 `docker compose pull || true`，拉取失败继续跑，把来源失败静默成「用本地缓存」。
- `config.json` 由 heredoc 把 `DB_PASS` 直接展开写盘，权限随 umask，引号缺失就多一层展开。

升级侧 `update.sh` 三点：`sync_repo` 用 `git pull --ff-only`（只允许快进，非快进即停手，不 merge）；docker 分支只 pull 应用服务名，不 pull 钉死版本的 DB 服务；本地编译分支 `CGO_ENABLED=0 go build -trimpath -o <bin>` 直接覆盖同名文件，不校验产物摘要，这一路的完整性由源码可信度承担，与自升级链的校验无关。

## 失败模式与判据

| 局面 | 判据 |
|---|---|
| 暂存件校验不过 | `cleanStaged` 删 New 与 Sum、删 marker，`State.FailedStage=true`，`Continue` 跑旧版；日志「暂存的新版本未通过校验，已丢弃」 |
| exec 级故障 | `smokeTest` 用 `-h` 拉起，30s 超时、非 0 退出、空文件、包内找不到同名基名（`path.Base` + `EqualFold` 匹配，不解压整棵树，天然不吃 zip 路径穿越）都算失败 |
| 换装失败 | `State.FailedStage=true` 且当前版本字节不变，测试断言「校验失败时当前版本一个字节都不动」 |
| 起得来但初始化崩 | 端口占用、DB 迁移炸、配置不兼容 → 靠 `attempts` 计数，第 4 次启动触发回滚 |
| 回滚也失败 | 删 marker，按当前状态继续起，日志留因，避免无限重启 |
| 容器内升级 | `InDocker()` 查 `/.dockerenv` 与 `/proc/1/cgroup`，命中说明换装写的是容器可写层，重建容器即退回镜像版本，前端要把这句讲明白 |
| 冒烟递归 | 子进程带 `smokeEnv`（`<自名>_SELFUPDATE_SMOKE`）非空时 `Bootstrap` 直接 `Continue` |
| 同机篡改窗口 | 暂存件与 `.sha256` 同在可写目录，能改暂存件的进程也能同时改摘要 —— 二次校验只挡传输损坏，不挡同机改写 |

## 与既有卡衔接

- `ai-infra-security/AI-Infra-Guard-Tencent`：装之前先查目标 tag 对应组件的已知 CVE，决定停在哪一版。
- `cloud-security/cicd-poisoning`：zip 与 SHA256SUMS 的投毒面在 CI 侧，本卡只做消费端拒收。
- `windows-post/evasion`：镜像与二进制替换的落地点、持久化手法，与本卡的 rename 换装顺序互为对照。
- `tgsec-arsenal-router`、`tgsec-suite`：按「自升级 / 供应链 / 换包 / 回滚」症状检索时命中本卡。
