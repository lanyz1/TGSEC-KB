<!-- archived from /root/.hermes/skills/data-engineering/bulk-dir-linux-to-windows/SKILL.md on 2026-10-21 -->

---
name: bulk-dir-linux-to-windows
description: Move a huge dir from Linux server to Windows PC.
---

> 归档卡：原目录 `/root/.hermes/skills/data-engineering/bulk-dir-linux-to-windows`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/data-engineering/bulk-dir-linux-to-windows/…')`，不要相对 `references/legacy/` 解析。

# 大目录 Linux → Windows 搬迁(27 GB / 38 万文件实证)

场景:把服务器上几十 GB、几十万文件的目录搬到 Windows 本机 D 盘,链路受限
(直连 0.05 MB/s、跳板出带宽 0.4 MB/s)、文件名含中文 / `?` `"` `\` / 控制字符。

## 0. 先侦察(别急着传)

```bash
du -sh DIR; find DIR -type f | wc -l; find DIR -type d | wc -l
find DIR -type l | wc -l                                       # 符号链接数量,后面单列
find DIR -type f -printf '%s\n' | awk '{s+=$1} END {print s}'   # 精确字节
for t in tar gzip zstd pigz rsync; do command -v $t; done       # 服务器有啥
```

先建 SSH 免密(比反复喂密码稳,原生 ssh/scp 也比 paramiko 快):
本地生成 ed25519 key → paramiko 上传公钥追加到 `/root/.ssh/authorized_keys`(chmod 600)→ 后续全用
`ssh -i key -p PORT -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@HOST`。

## 1. 服务器端压缩(必做,省一半流量)

```bash
cd /root && tar -cf - DIR | zstd -6 -T0 -o /root/DIR.tar.zst
```

HTML/JSON 导出数据压缩率 ~54%,27 GB → 14 GB。可压缩文本用 -6,纯二进制用 -1。
后台跑:直接 `setsid bash -c '...' </dev/null >/dev/null 2>&1 &`;
若用 `exec_command`,**不要读 stdout**(后台进程不关 fd 会挂住),改为轮询产物文件大小。

同时 `sha256sum /root/DIR.tar.zst > /root/DIR.sha256`(最后校验用)。

## 2. 通道:机场订阅 → mihomo 多节点并行(关键提速手段)

**先测清楚**:单流分别测 直连 / 每个本地代理端口 / 每个 SSH 跳板。
- 症状:单流一开始 3.4 MB/s 然后衰减到 0.3 —— 是**机场账号级限速**,不是链路断。
- 4 条流并行跑同一节点,总吞吐反低于单流 → **节点总带宽封顶**,该节点并行无意义。
- 国内跳板出带宽常只有 1–5 Mbps(0.4 MB/s),别指望拿它中转。

**换多节点并行**:机场订阅直连拉(经代理常 403)、base64 解出 vless 节点 → 写 mihomo 配置,
每个节点一个 socks listener:

```yaml
proxies:
  - {name: hk, type: vless, server: 1.2.3.4, port: 443, uuid: UUID, network: tcp,
     tls: true, flow: xtls-rprx-vision, servername: SNI, client-fingerprint: chrome,
     reality-opts: {public-key: PBK, short-id: SID}}
listeners:
  - {name: hk-socks, type: socks, port: 11010, proxy: hk}
```

`mihomo -f conf.yaml -d . -t` 先验配置;启动后 `netstat | grep 1101` 确认在听。
逐节点测速(连目标 SSH 端口下 8–20 MB 样本),取前 6 个并行 —— 实测 6 通道叠加把 0.3 MB/s 拉回稳定 3.0 MB/s。
**此时瓶颈常已变成服务器出口带宽**(服务器上 `curl -o /dev/null speed.cloudflare.com/__down?bytes=50000000` 可测上限)。

## 3. 分段并行下载(可续传)

```python
cmd = "tail -c +%d %s | head -c %d" % (start + have + 1, REMOTE, length - have)
i, o, e = cli.exec_command(cmd, timeout=60)
o.channel.settimeout(60)
with open(part, "ab") as f:                 # 追加,天然断点续传
    while True:
        try:   d = o.channel.recv(262144)
        except socket.timeout: continue
        if not d: break
        f.write(d)
```

每段 5 次重试(换节点),产物 `parts/partN`,最后顺序拼接。**任一段失败必须补齐**。
若发现某段已有残留(tar 分段产物),先本地算 sha256 与服务器
`tail -c +N file | head -c LEN | sha256sum` 比对,一致就复用,省重传。

## 4. 解压:必须用 Python tarfile(血泪点)

**MSYS/GNU tar 和 Windows 自带 bsdtar 都会把 tar 里的 UTF-8 文件名按 GBK 解释**,
解出 `娴嬬粯寮曟搸` 这种乱码目录,部分条目还报 `Invalid empty pathname: Unknown error`。
**别浪费时间去调它们**,直接:

```python
import zstandard, tarfile
dctx = zstandard.ZstdDecompressor()          # pip install zstandard
with open(SRC, "rb") as f, dctx.stream_reader(f) as reader:
    tf = tarfile.open(fileobj=reader, mode="r|", encoding="utf-8")
    for m in tf:
        tf.extract(m, path=DEST, set_attrs=False)   # set_attrs=False 免权限报错
```

速度 ~4000 entries/s,38 万条目 1.8 分钟。

## 5. Windows 文件名净化(必做,否则丢数据)

非法字符 `< > : " \ | ? *` **加上 0x00–0x1F 控制字符**(实测会遇到
`package-c\x01mmon`、`weui-mini\x01rogram`)→ 一律换 `_`,再去尾部空格和点:

```python
def clean_part(p):
    p = "".join("_" if ord(c) < 32 or c == "\x7f" else c for c in p)
    for ch in '<>:"\\|?*': p = p.replace(ch, "_")
    return p.rstrip(" .") or "_"
```

**致命坑:不同原名净化后可能撞名**。本次 68 组(如 `x_\\_.xml` 与 `x_四个下划线.xml`)
被静默互相覆盖 → 内容错。必须**按清单纯顺序给后来者加 `~1`/`~2` 后缀**:

```python
for c, items in groups.items():          # groups: 净化名 -> [(原路径, 大小)]
    for i, (p, sz) in enumerate(items):
        tgt = c if i == 0 else "%s~%d" % (c, i)
```

补缺时按 tar 流重扫:目标已存在且大小对就跳过,其余按 `tgt` 写入(38 万条目 0.4 分钟)。

## 6. 权威验证:全量清单比对(别只抽样)

```bash
find DIR -type f -printf '%s\t%p\n' > /root/filelist.txt   # 38 万条约 47 MB
find DIR -type l -printf 'L\t%p\n' >> /root/filelist.txt
```

拉回本地,用**同一套净化+冲突规则**逐条比大小:`matched / missing / sizediff`,并反向找 extra。
符号链接要用 `os.path.lexists` 判 —— 断链链接的 `exists` 返回 False,会误报上千条缺失。

## 7. Windows Defender 会吃掉渗透工具(常被忽略)

`frpc` / `chisel` 等被判 HackTool,**落地瞬间即被删除**,并留威胁记录:
```powershell
Get-MpComputerStatus | Select RealTimeProtectionEnabled
Get-MpThreatDetection | Sort InitialDetectionTime -Desc | Select -First 5
```
恢复:先 `Add-MpPreference -ExclusionPath 'D:\DIR'` 再解压,用完 `Remove-MpPreference`;
或把工具单独存 zip(Defender 不扫 zip 内容)。

## Pitfalls

- 后台任务的完成通知会**延迟很久**才到,可能是几十分钟前已处理完的阶段日志 —— 别当成新问题重新排查。
- `du -sh` 与逐文件字节求和不一致是正常的(du 算块对齐)。
- 解压后立刻统计可能拿到中间态(异步写入未刷完),等多秒再统计。
- 打包归档 `.tar.zst` **先别删** —— 唯一原始字节证据,被 AV 拦掉的条目随时能从它单拉:
  `zstd.exe -dc a.tar.zst | tar.exe -x -C D:/ "DIR/path/to/file"`。
- 同目录若出现来源不明产物(如 `_av_blocked_tools.zip`、临时目录),说明**有另一个会话在动同一份数据**,
  先确认无并发写再继续,否则互相覆盖。
