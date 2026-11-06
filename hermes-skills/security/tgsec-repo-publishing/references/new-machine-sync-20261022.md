# 新机器全量库同步（2026-10-22 实测，两台各一遍）

场景：用户丢一句「`<LAB-HOST-n>` 也给同步更新上，账号密码都一样」。目标机已有一套精简库 + 一个落后仓库，没有检索工具链。

> 本文用 `<LAB-HOST>` / `<LAB-HOST-2>` 代替真实地址：这份库会被打成分享包发出去，写回去等于把刚脱敏的自有 IP 又带一遍。

## 探测（一律先跑，别猜）

| 项 | `<LAB-HOST>`（第一台） | `<LAB-HOST-2>`（第二台） |
|---|---|---|
| hostname | `ser…`（省略） | `ser…`（省略） |
| CPU / 内存 | 8 核 / 7G | 8 核 / 7G |
| 磁盘 | 49G，用 27G | 49G，用 40G，剩 8.9G |
| 安装库卡数 | 164 | **160** |
| `~/.hermes/arsenal` | 空 | **空**（没跑过门禁） |
| 仓库 HEAD | `7e2812b1` | `b401bbe1` |

判读：

- `~/.hermes/arsenal` 为空 = 这台机器从来没有索引/门禁，**它此前任何「库正常」的说法都没有证据**。
- 磁盘只剩个位数 G 也能装（库 150M + db 348M），但别在里面留旧备份和临时包。
- 精简库卡数不等于「坏了」：两台都是 160~164 张的薄装机，portable 是正确结论。

## 搬运（口令不出案卷机）

```bash
# 案卷机
cd /root/arsenal-share
P=$(cat PASSPHRASE.txt)
gpg -q --batch --passphrase "$P" -d hermes-skills-20261022-1912.tar.gz.gpg > /tmp/lib1912.tar
sha256sum /tmp/lib1912.tar | tee /tmp/lib1912.tar.sha256
scp /tmp/lib1912.tar /tmp/lib1912.tar.sha256 root@<LAB-HOST-2>:/tmp/

# 目标机
cd /tmp && sha256sum -c lib1912.tar.sha256   # 必须 OK
```

实测：`tar_bytes=43,147,706`、`/tmp/lib1912.tar: OK`。

**为什么不在目标机解密**：口令就得多落一处；目标机还得装 gpg。明文 tar 反正一样要落地，不如只传它。传完 `rm -f /tmp/lib*.tar*`。

## 安装

```bash
# 1 精简库挪开（不删）
mv ~/.hermes/skills /root/skills.thin-20261022     # 记录原卡数：160

# 2 解包
tar xzf /tmp/lib1912.tar -C ~/.hermes
find ~/.hermes/skills -name SKILL.md | wc -l        # 期望 = 包内卡数 2171
python3 -c 'import json;print(len(json.load(open("/root/.hermes/skills/.disabled.json"))))'   # 期望 1805

# 3 仓库对齐（不用 pull）
cd ~/TGSEC-Qtzuu && git fetch -q origin master && git reset -q --hard origin/master

# 4 一条脚本：拷工具栈 + md5 自检 + 重建 + 门禁
bash scripts/apply-arsenal-20261022.sh > /tmp/apply.log 2>&1; echo APPLY_RC=$?
```

## 验收（三证，缺一条不算完）

```json
{"total": 2171, "enabled": 397, "disabled": 1774, "legacy": 1856}
GATE OK（full）· 2171 卡 / 2171 张 | 30/30 | 94/96 · 96/96 · MISS 0 · 标题 8/8 · 正文 7/8
tier=full  skipped=0  ok=true
```

外加**检索实证**（门禁绿 ≠ 查得出来）：

```bash
SKILL_FIND_NOLOG=1 python3 ~/.hermes/arsenal/skill_find.py "1win 平台 打点" --phase recon
# 1. [E] 1win-platform-pentest  score=2028.5  cat=security
```

## 坑

- **`apply` 脚本不是纯重建器**：它第一步把 `tools/arsenal/*` 从仓库拷到 `~/.hermes/arsenal` 并逐个 md5 自检；目标机 `~/.hermes/arsenal` 为空时这正是补工具链的动作，所以**必须先 reset 仓库再跑脚本**。
- **`git reset` 只动仓库工作树**，不碰 `~/.hermes/skills`；反过来解包也不动仓库。两件事互不覆盖，顺序无所谓，但都要做。
- **`.tgsec-bootstrapped` 会让 `dirty` 永远非 0**：`bootstrap.sh` 写在仓库根，`.gitignore` 缺这两行时 `git status --porcelain` 一直有 `?? .tgsec-bootstrapped`。已在 `.gitignore` 补 `.tgsec-bootstrapped` / `.tgsec-bootstrapped.*`（commit `ef5287ca`），两台 `reset --hard` 后 `dirty=0`。
- **精简库要留档**：`/root/skills.thin-<date>` 是下一轮「吸收独有卡」的唯一来源（第一台的 166M 混合库出过 31 张独有卡、25 张真卡入主库）。
- **别用 `git pull`**：这批历史 amend 过，`pull` 会 `divergent branches`；统一 `fetch + reset --hard`。
