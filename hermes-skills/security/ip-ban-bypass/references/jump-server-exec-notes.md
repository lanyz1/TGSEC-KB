# 跳板机远程执行 —— 实战踩坑与规范姿势

> 补充本技能 §2「出口来源与纪律」的多机并行探测场景。
> 配套脚本:`scripts/ratelimit_curve_probe.py`(限流 vs 绕过 判定)

## 1. 多机并行 exec 的规范姿势

**别内联 heredoc。** 通过 paramiko `exec_command` 跑远程 python 时,
`python3 - <<'EOF' ... EOF` 这种写法经过本地 shell → ssh → 远程 bash **多层二次解析**,
嵌套引号必然崩:

```
bash: eval: syntax error near unexpected token `('
bash: line 15: warning: here-document ... delimited by end-of-file
```

**正确姿势(本次稳定跑通)**:

1. 本地写好 `.py` 文件
2. sftp 上传到跳板机 `/root/<name>.py`(或放到工作目录)
3. `exec python3 /root/<name>.py` 执行

实现要点(本次用的 ~10 行 helper):`paramiko.SSHClient` + `AutoAddPolicy`
→ `open_sftp().put(local, remote)` → `exec_command(cmd)` 读 stdout/stderr + `recv_exit_status()`。
**把 host 表写成 dict**(`{"宁波": (ip, port, user, pwd), ...}`),循环里 `put` + `run` 即可逐台跑同一脚本。

## 2. `%` 格式化的陷阱

远程脚本**模板里含 `%d` / `%s` 时,不要用 `%` 格式化去拼占位符**:

```
REMOTE = """... url.encode() ... %d format ...""" % mode   # ✗
# -> TypeError: %d format: a real number is required, not str
```

改用 `.replace("__MODE__", mode)`。否则模板里的每一个 `%d/%s` 都会参与格式化。

## 3. `pkill -f` 会杀掉自己

`pkill -f <pattern>` 匹配**整条命令行**。当你的执行方式是
`bash -c "... pkill -f foo ..."` 时,那层 `bash -c` 的命令行**本身就含 `foo`** → 自杀,
调用方拿到空输出 + `EXIT -1`。

**改法**:

```bash
ps -ef | grep "[f]eed_poll" | awk '{print $2}' | xargs -r kill
```

- `grep "[f]eed_poll"` 的方括号让 grep **自身**不匹配
- **清理与启动分两次 exec**,别写在同一条命令里
- 长驻进程用 `setsid nohup python3 x.py >> x.log 2>&1 &` 拉起后,
  **改看日志文件判断存活**,不要再用 pkill 去找它

## 4. 跳板机池状态(2026-09)

详见 `references/jump-servers.md`。要点:

| 名称 | 状态 |
|---|---|
| 宁波电信 `110.42.103.114:56102` | ✅ 可用(密码已更新为 `[REDACTED]`,旧 `3KPtV1vx` 失效) |
| 内蒙古 `43.240.221.227` | ✅ 可用 |
| 绍兴 `124.248.67.181` | ✅ 可用 |
| 深圳 `103.109.21.198:22` | ⚠️ 本次 TCP 22 连不上,待复测,**别当常备出口** |

> 跳板机**不可达属于环境状态、会变**,标注时写清日期 + "待复测",
> 不要写成永久结论 —— 否则未来会把一台已恢复的机器当成死的。

## 5. 出口差异不代表技巧有效

同一条请求在不同出口上返回**不同错误码**,很容易被解读成"这个出口能绕过"。
本次实测:宁波返回 `errno:0 "too fast"`,内蒙古/绍兴返回 `errno:2`。
追下去发现差异来自**该 IP 已被打满请求配额**,与出口"干净程度"无关。

**判据**:换出口后要用**计数复现 + 跨环境基线**确认,见
`scripts/ratelimit_curve_probe.py` 与
`pentest-finding-verification/references/throttle-camouflaged-bypass.md`。
