# 跳板机预检与「exec 静默」诊断(长任务前必做)

## 症状 → 判定矩阵
| 症状 | 判定 | 处置 |
|---|---|---|
| 本地日志只有 `rc=124` + 远端产物不存在 | 远程脚本根本没起来 / 通道挂起 | 换机,或改 `nohup &` + `get` |
| `exec` 零输出,但 `get <远端路径>` 能取到文件 | **exec 静默**(通道不关,远端其实已跑完) | 一律 `nohup` + `get`,**别信 `exec` 的 stdout** |
| `get` 报 `FileNotFoundError` | 远端确实没产出 | 先跑 preflight 确认解释器/依赖 |
| 远端 tee 文件不存在,但脚本第 1 行就 `open(...)` | 解释器在导入阶段就崩了(或没启动) | 查依赖/查是否真的上传了脚本 |

## 强制预检(长任务前,1 次 exec + 1 次 get,`<5s`)
先把这段写成 `preflight.py`:
```python
import sys
with open("/tmp/preflight.txt", "w", buffering=1) as f:
    f.write("python=%s\nexe=%s\n" % (sys.version.split()[0], sys.executable))
    for m in ("requests", "paramiko"):
        try:
            __import__(m); f.write("%s=ok\n" % m)
        except Exception as e:
            f.write("%s=FAIL %s\n" % (m, e))
    f.write("done\n")
```
跑:`python jump_run.py exec <host> preflight.py python3` → 再 `python jump_run.py get <host> /tmp/preflight.txt pf.txt`
⇒ 一次拿两件事:**解释器/依赖是否可用** + **exec/get 通道是否健康**。
实测:`@ningbo` = `python=3.12.3` / `requests=2.31.0 ok` / `paramiko` 缺(仅供 HTTP 任务时无所谓),但 **exec 零输出、get 正常**。

## 长任务正确姿势(避免 `rc=124` 假死)
- **不要** `timeout N python jump_run.py exec <host> <script>`:`timeout` 掐的是**本地** jump_run.py,
  远端可能早已跑完或被挂起 ⇒ 你只会拿到 `rc=124` + 零证据。
- **正确**:远端段落自己 `nohup` 后台化并落**带唯一时间戳**的产物:
  `nohup python3 <script> > /tmp/<name>.<ts>.out 2>&1 &`
  然后周期性 `python jump_run.py get <host> /tmp/<name>.<ts>.out <local>` 边跑边取。
- 产物名**必须带唯一时间戳**(或跑前 `cp` 留存):否则下一次跑的 `rm -f`/同名覆盖会把上一跑的
  「0 命中 / 42 段完成」这类**独有证据**抹掉(实测踩过三次)。
