# cron 脚本语言 + 把进度「推」到用户面前(2026-09-15 实测)

> **更正** `unattended-automation-integrity-and-scale-estimation.md` 第二/三节:
> 「退出码陷阱」真实存在,但**不是**那次 `last_status: error` 的原因。本文件给出真凶。

## 一、作业报 error 时,先读 stderr,别猜退出码

`cronjob list` 只给一个 `error` 标签。我照脑内「退出码假设」先改了一轮脚本 —— **纯属白改**。
把它**手动 run 一次**,读返回块里的 `stderr` / `Partial output`,真凶一秒现身:

```
wsl: A localhost proxy configuration was detected but not mirrored into WSL.
<3>WSL (14 - Relay) ERROR: CreateProcessCommon:818: execvpe(/bin/bash) failed: No such file or directory
```

**机制**:调度器按扩展名分派解释器 —— `.sh`/`.bash` **走 bash**;这台 Windows 上 bash 落到
**已损坏的 WSL** ⇒ `execvpe` 失败 ⇒ **脚本一行都没执行**,重启 worker / 回传 / 刷桌面包
**全部静默没做**,而作业只显示 `error`。

**⇒ 铁律:看到 `error`,第一步是「手动 run + 读完 stderr」,不是改脚本。**

## 二、修复:cron 脚本一律用 `.py`

```python
BASH = r"D:\Git\usr\bin\bash.exe"     # 用 cygpath -w /usr/bin/bash 查出本机落点
subprocess.run([BASH, "-lc", cmd], cwd=BASE, timeout=900)
```

需要 shell 语法时**由 Python 显式调 git-bash**,绝不把解释器选择权交给调度器。
(`EXEPATH=D:\Git\bin` 是干扰项,别拿它拼 bash 路径。)

## 三、调度语法的两个坑(都踩过)

- **`schedule='30m'` 被解析成「一次性」**(`repeat: once`),跑完就停;
  循环必须写 **`every 30m`** ⇒ 才是 `repeat: forever`。
- **`deliver` 不显式写 `origin`,`no_agent` 作业会落到 `local`**(只存不发,用户永远看不到)。
- 已验证可用组合:`no_agent=True` + `script='xxx.py'` + `deliver='origin'`
  ⇒ stdout **真的**作为新消息进对话(用户端可见)。

## 四、cron 入口必须「秒级返回」

原 `.sh` 入口要跑 6 个重启脚本 + 回传 ≈ 10 分钟,被工具/调度超时打断,**每次都白跑**。
改为:cron 入口只**加锁 + 后台脱钩 + 立即返回**。

```python
DETACH = 0x00000008 | 0x00000200        # DETACHED_PROCESS | NEW_PROCESS_GROUP
subprocess.Popen([BASH, "-lc", FULL], cwd=BASE, creationflags=DETACH)
```

配套:锁文件防重入(上轮未跑完则跳过并打印原因,不要静默 return)。
实测入口 **0.059 秒**返回,重活在后台跑完自己 `rm -f` 锁。

## 五、用户不会去开你的 UI 控件 —— 进度要「推」,不要「拉」

用户原话:「**看不到直接给我反馈进度吧**」。
该轮我先交了:桌面 HTML/MD 文件 + 桌面插件面板(右栏/底栏/状态栏芯片)。
**用户仍说看不到。** ⇒ 长跑里「进度可见性」= **每 N 分钟一条自动消息进对话**,
不是给他一个要去点开、去刷新、去 reload 的东西。

**排序:①自动推消息进对话(首选,已验证) → ②对话框里我一开口第一句报进度 → ③桌面文件兜底 → ④UI 插件(最末)。**
自动播报内容固定含:**总量+完成度 / 关键字段计数 / 速率 / 剩余 ETA / 进程与出口健康 / ⚠️异常告警**。
进程数骤降要**主动标警**(本次 45→11 未告警,靠人工看得出,不合格);增量口径要写清
「本地镜像新增」,否则回传补齐造成的跳升会被当成真实新采(用户会误解)。
