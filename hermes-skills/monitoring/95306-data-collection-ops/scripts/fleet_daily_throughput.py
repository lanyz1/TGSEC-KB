# -*- coding: utf-8 -*-
"""95306 机队当日产能 sweep(只读)。

在哪跑:主服上跑(用 `python`,不是 `python3` —— paramiko 装在 3.11;经 mrun.py 投递亦可)。
做什么:读 /opt/v6/jumpers.json(字段 ip/pwd)逐台 SFTP 推 shell 脚本 -> `bash /tmp/_tp.sh`
        输出 轮次/整机冻结/账号冻结/完成/零产出/新企业包件/识别/state_mtime —— 日志源自动分支。

判读:①某台 R=0 先看 state_mtime,新鲜 = 只是日志源不对(不是没跑);
      ②零产出占比 ≈97% 属当前病态基线,根因见 references/collector-cooldown-and-throughput-forensics.md。
"""
import json
import paramiko

QS = r'''#!/bin/bash
T=$(date +%m-%d)
if [ -s /opt/v6/v6_run.log ]; then S=v6_run.log; grep "$T" /opt/v6/v6_run.log > /tmp/_tp.log 2>/dev/null
else S=journald; journalctl -u v6collector --since today --no-pager > /tmp/_tp.log 2>/dev/null; fi
L=$(wc -l < /tmp/_tp.log)
R=$(echo "$(grep -c 轮询开始 /tmp/_tp.log)")
COOL=$(echo "$(grep -c 风控冷却 /tmp/_tp.log)")
ESC=$(echo "$(grep -c 冷却升级 /tmp/_tp.log)")
FIN=$(echo "$(grep -c 轮询完成 /tmp/_tp.log)")
ZERO=$(echo "$(grep 轮询完成 /tmp/_tp.log | grep -c '新企业包件 0, 识别 0')")
PKG=$(grep 轮询完成 /tmp/_tp.log | awk -F"新企业包件 " '{print $2}' | awk -F, '{s+=$1} END{print s+0}')
IDN=$(grep 轮询完成 /tmp/_tp.log | awk -F"识别 " '{print $2}' | awk -F, '{s+=$1} END{print s+0}')
SM=$(stat -c %y /tmp/v6_state.json 2>/dev/null | cut -d. -f1)
echo "src=$S L=$L R=$R COOL=$COOL ESC=$ESC FIN=$FIN ZERO=$ZERO PKG=$PKG IDN=$IDN state_mtime=$SM"
'''


def main():
    js = json.load(open("/opt/v6/jumpers.json", encoding="utf-8"))
    for name, j in js.items():
        ip, pw = j["ip"], j["pwd"]
        try:
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c.connect(ip, 22, "root", pw, timeout=30, banner_timeout=90, auth_timeout=90)
            with c.open_sftp().open("/tmp/_tp.sh", "w") as f:
                f.write(QS)
            _, so, _ = c.exec_command("bash /tmp/_tp.sh", timeout=120)
            print("==", name, ip, so.read().decode("utf-8", "replace").strip())
            c.close()
        except Exception as ex:                      # 通道抖动是常态,单台失败不影响其余
            print("==", name, ip, "FAIL", type(ex).__name__, str(ex)[:80])


main()
