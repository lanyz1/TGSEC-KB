---
name: linux-disk-reclaim
description: "Use when a Linux/VPS disk is filling: reclaim space."
version: 0.1.0
tags: [disk, cleanup, vps, ops, cache, teardown]
---

# Linux/VPS 磁盘回收（先审计再回收，按实测收益排序）

触发：`还能清理磁盘吗` / `df` 告急 / 清场交接之后。**先 `du` 分层定位大头，再动刀；每一刀都有再获取路径（缓存可重建、工具可重装）才删。**

## 审计（1 分钟定位大头）

```bash
df -h / | tail -1
du -sh /root/* 2>/dev/null | sort -rh | head -20
du -sh /var /usr /opt /tmp /home 2>/dev/null | sort -rh
du -sh /var/* 2>/dev/null | sort -rh | head -12
# 两个常见巨坑的定位：
du -sh /root/.local/share/uv/tools/* 2>/dev/null | sort -rh | head -20
du -sh /var/lib/snapd/* 2>/dev/null | sort -rh
```

## 回收菜单（2026-10 实弹数字，按收益）

1. **snapd 下载缓存（~2.7GB，最肥的隐形坑）**：`rm -rf /var/lib/snapd/cache/*`——纯下载缓存，需要时 snapd 会重下。顺手清废弃版本：`snap list --all` 找 `disabled` 的 `snap remove --revision <rev> <name>`；`snap set system refresh.retain=2` 防再堆积。
2. **巨型 uv 工具（单体可达 5GB+）**：`du -sh ~/.local/share/uv/tools/*` 逐个称重——LLM 类工具（garak=5.2GB，拖 torch/CUDA 依赖）通常是最大单体。`uv tool uninstall <name>`，要用时重装（几分钟）。**只砍认识且近期不用的**。
3. **journal**：`journalctl --vacuum-size=50M`（实测 440M+ 可回收）。
4. **公网 VPS 的爆破日志（~250MB+）**：`truncate -s 0 /var/log/btmp /var/log/btmp.1 /var/log/auth.log` + 删 `*.log.1` 轮转档——SSH 被扫的失败记录会涨到几百 MB。
5. **包管理器缓存**：`apt-get clean` + `rm -rf /var/cache/apt/archives/*.deb`；`go clean -modcache`（GOPATH 缓存，~400MB；go/bin 里的工具二进制**别动**）。
6. **浏览器双份缓存**：(a) 内核 `~/.cache/ms-playwright`（实测 654MB）——只在确认近期不做浏览器自动化时删，恢复 = `playwright install`；(b) **长跑 CDP profile 的缓存目录** `<user-data-dir>/Default/{Cache,Code Cache,GPUCache,Service Worker}`（实测单 profile ~717MB，Cache 独占大头）——登录态/Cookies 在别的文件，浏览器在跑也能删（unlink 不影响运行，进程会自行重建）。
7. **工作区/载荷**（战役清场后）：`rm -rf` 前先 `du -sh` 报数 + **抽样验证内容**（`ls` / `find | wc -l`——记忆中的体积常与盘上不符，实测把 5.9G 记成 2.3G）；用户已明确表态不要的数据类可直接删（如被说过「我要这个干嘛」的 KYC 证件库）；确认已交付/已归档再删；保留 ≤10MB 笔记。
8. **进程持有的已删文件（df 满但 du 找不到大头时的第一嫌疑人）**：`lsof +L1 2>/dev/null | awk '$7 > 1000000000 {print $1, $2, $7/1048576 " MB", $9}'`。典型案例：长跑浏览器自动化/CDP 批量下载后 **Chrome 累积 ~10GB 已删除缓冲**（反复爆盘真凶，实测单次 6.8GB+4.5GB），**重启 Chrome 立即释放全部**。配套：重启脚本用原 `--user-data-dir` 即保留登录态（cookies 落盘）；重启后要重开业务标签页并重启依赖它的驱动脚本。长跑会话 = 周期性复发 → 进看护 loop（见坑）。
9. **证据图压缩（图矿类工作区的大头）**：PNG/BMP → JPEG（`PIL` max边 1280、quality 78）**约省 60% 且保持可读证据**（实测 3,800 张 3.8G→1.6G）；给转换加 **mtime 年龄门**（如 <10min 的文件跳过，避开正在写入的新文件）——手动跑与看护自动跑共用同一脚本。
10. **已处理的大 CSV → `gzip -9` 原地压缩保留**（压缩 40–70% 且 zcat 可再用，比重删安全；已榨取/可再导出的中间文件才直接删）。
11. **先抽价值 → 验证 → 再删原件**（大 dump 清理铁律）：删前先抽紧凑派生物——去重令牌（`grep -oE … | sort -u`）、配对/映射文件（大 CSV → 密文对/ID 索引）、把散份索引合并成一份；`ls` 验证派生物落盘后再 `rm`。**带断点续跑的任务（扫描器/提取器）删其源文件 = 砍断续跑**——先确认任务确已终态再动。
12. **`/tmp` 历史抓站残留 + snap Chromium 私有 tmp（实测 1.8G → 1.4M）**：先 `du -sh /tmp/* 2>/dev/null | sort -rh | head -20` 定位，大头常是 `/tmp/snap-private-tmp/snap.chromium`（snap 版 Chromium 的私有 tmp，浏览器退出后**不自动清**，实测单目录 1.7G，纯僵尸可直接删），其余是几百上千个 `.b/.hdr/.html/.txt` 抓取碎片（实测 907 个条目 / 125M）。清理走白名单，别 `rm -rf /tmp/*`：
    ```bash
    KEEP='^(snap-private-tmp|systemd-private-.*|\.ICE-unix|\.X11-unix|\.XIM-unix|\.font-unix|\.Test-unix|hsperfdata_root|hermes_kernel_.*|playwright-artifacts-.*|org\.chromium\.Chromium\..*|node-compile-cache|trae)$'
    for p in /tmp/* /tmp/.[!.]*; do b=$(basename "$p"); echo "$b" | grep -Eq "$KEEP" || rm -rf "$p"; done
    ```
    保留 `snap-private-tmp` 目录本身、只删其下的 `snap.chromium`；清完复核 `du -sh /tmp` + `ls -A /tmp | wc -l`（本例 1,009 → 13 个条目），别把 `/tmp` 清成空目录影响 X11/systemd socket。

## 不动的（再缺也别碰，重装成本高）

- 在用工具链：`/root/go/bin`（渗透 Go 工具集）、uv tools 里在用的（impacket/frida-tools/pwntools/netexec/mobsf…）、语言 SDK。
- 知识库/证据/交付留档：如 `TGSEC-Qtzuu`、`*-delivery/`、冻结的证据目录（用户数据删除前必须先问）。
- 昂贵构建产物：blutter（Dart/NDK 重建约半小时）、已配置好的 venv。

## 验证与报告

- 前后 `df -h /` 对比；报「释放 X GB + 现状（已用/空闲/百分比）」。
- 对用户只报大头归类 + 数字（例：uv 巨工具 -5.2G / snap 缓存 -2.8G / 日志 -1.3G），别列流水账。
- 给出「还可以再挤但没动的」候选清单（留一个下一轮的余地，用户常会追问第二轮）。

## 坑

- `du -sh /var/lib/snapd` 顶层看不大——大头在 **cache/ 子目录**，必须逐层钻。
- `uv cache clean` 只清 `~/.cache/uv`（KB 级）；**工具本体在 `~/.local/share/uv/tools/`**，两者常被混淆（实测清了 96KB 还以为清完，7GB 纹丝不动）。
- 删除会话进行中的目录（正在下载/正在跑的任务工作区）会连带杀任务——先停任务再删文件。
- 前台命令长时间等待有硬顶（本机 ~420s）：大批量删除/校验放后台跑。
- **`snap remove --revision N` 会抽走正在运行的进程脚下的二进制**：删了正在用的 disabled 修订版（如 chromium 旧 rev）后，那个进程一死就再也起不来（`No such file or directory`）。删修订前先 `ps` 看谁在用；重启脚本里改用 **`/snap/<pkg>/current/usr/lib/...`** 这类滚动路径，别硬编码修订号。
- **爆盘是复发性问题就上自愈 loop，别一次次手动救**：常驻脚本每 5–10 分钟做「triage 删无用物 + 空闲<4G 自动压缩 + 空闲<5G 且浏览器脏缓冲>2G 自动重启浏览器并重挂依赖 + 空闲<1.2G 急停下载器」。手动清理只解决当下，loop 解决复发（本案例一天三次爆盘 → 上线后归零）。
- `df` 显示已用而 `du -x /` 对不上账（差额 GB 级）= 已删但被进程持有的 inode——先 `lsof +L1`，别盲目扩大删除范围。
- **`du -sh /tmp` 报 1.8G、顶层文件加起来却只有几百 M** = 大头在 `/tmp/snap-private-tmp`（snap 应用私有 tmp，Chromium 一家独吞）；必须 `du -sh /tmp/*` 钻进去，光看 `ls -la /tmp` 会漏掉这个隐藏目录（名字以 `snap.` 开头，不在常规抓取残留清单里）。
- 清 `/tmp` 的判断口径：**普通文件/抓取碎片可全删，运行时目录必须留**（`systemd-private-*`、`.ICE-unix`/`.X11-unix`、`hsperfdata_root`、`hermes_kernel_*`、`playwright-artifacts-*`、`org.chromium.Chromium.*` 可能是活会话的临时目录）。`snap-private-tmp` 删内容不删目录。
