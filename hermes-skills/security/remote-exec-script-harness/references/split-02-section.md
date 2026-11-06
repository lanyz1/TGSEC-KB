## 骨架形态

```python
# 本机 <name>.py
import paramiko
HOST = ("<jump-ip>", 22, "root", "<password>")      # 凭据不写进报告与技能
REMOTE = r'''
# -*- coding: utf-8 -*-
import subprocess, sys, time, hashlib, binascii
def P(*a): print(*a); sys.stdout.flush()            # 远端必须 -u 或 flush,否则回显为空
...探测逻辑...
'''
c = paramiko.SSHClient(); c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST[0], HOST[1], HOST[2], HOST[3], timeout=30)
cmd = "cd /root/<work> && cat > r.py <<'PYEOF'\n" + REMOTE + "\nPYEOF\npython3 -u r.py 2>&1 | tee <name>.log"
si, so, se = c.exec_command(cmd, timeout=560)
print(so.read().decode("utf-8", "replace")[-11000:])   # 回显只取尾部,全量在 <name>.log
c.close()
```

