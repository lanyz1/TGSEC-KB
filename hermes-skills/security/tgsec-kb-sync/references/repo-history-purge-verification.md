# 仓库「净化/重写历史」复验

适用：仓库声称做过「撤全文卷 / 去密钥 / `git filter-repo` 重写全史 / 强推」后，需要**独立验证**泄漏是否真的从托管侧消失，以及量化还剩下什么。自报的「复扫 0 命中」不算证据。

## 1. 托管侧探测：旧对象到底还在不在

```bash
OWNER=lanyz1 REPO=TGSEC-Qtzuu SHA=<旧提交>; GH=https://github.com/$OWNER/$REPO

curl -s -o /dev/null -w '%{http_code} %{size_download}\n' $GH/commit/$SHA.patch      # 200 ⇒ 旧提交仍活（首选判据）
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' $GH/archive/$SHA.tar.gz   # 200 ⇒ 整包匿名可下
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://raw.githubusercontent.com/$OWNER/$REPO/$SHA/<旧敏感路径>"                 # 200 ⇒ 单文件直取
curl -s -o /dev/null -w '%{http_code}\n' "https://api.github.com/repos/$OWNER/$REPO/git/commits/$SHA"  # ✗ 404 会误导，不可作判据

curl -s "https://api.github.com/repos/$OWNER/$REPO" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['private'],d['forks_count'],d['stargazers_count'])"
```

- `.patch` = 200 就已经定案：**历史重写只换了分支指向，服务端的旧对象未被回收**。
- 父提交也要探：链式残留往往不止一个。
- `private=false` 且旧对象仍活 = 窗口开着（无论净化当时私有与否）。

## 2. 拿到旧归档后量化泄漏

```bash
curl -sL -o /tmp/old.tar.gz $GH/archive/$SHA.tar.gz && tar xzf /tmp/old.tar.gz -C /tmp/old_tree
find /tmp/old_tree -name '*.md' | wc -l
```

扫描器要求：
- 只输出 **[类别 / 文件 / 行号 / 长度]**，**不打印命中值**（输出进聊天就是二次扩散；报告里也不贴）。
- 分两档：真凭据（`sk-`、平台 `tga_`/`tgb_`、bot token、口令字面量、私钥头、AK/SK）与第三方 PII（手机号、身份证）。
- **已知误报要排掉**（否则报告全是噪声）：仓库自带的 `secret-patterns.md` / 字典文件、CVE PoC 文档里的示例 token、`AKIA…EXAMPLE`、`uv.lock`/锁文件的 base64 哈希、`JWT`/`18 位数字` 在文档中的提及。宣告「有/无」之前抽验命中上下文。
- 当前 `origin/master` 树要单独扫一次：**当前树干净 ⇒ 只是旧对象未回收**，这两个结论必须分开写。

## 3. 干净镜像验收（删仓重建的前置）

```bash
git clone --mirror <url> /root/<repo>-recreate.git
cd /root/<repo>-recreate.git
git cat-file -e <旧sha> 2>&1        # 必须失败（旧对象不在）
git ls-tree -r --name-only HEAD | grep -c 'case-reports'   # 必须 0
git rev-list --count HEAD; du -sh .
```

本机没有推送凭据 ⇒ 删仓重建**代跑不了**，把脚本 + 验收命令交给用户，并在报告里写明「未执行」。

## 4. 报告形状

分三块，不要混：
1. **硬事实**（HTTP 码/字节数/提交号/文件数/命中类别计数）——可复核的原始数码。
2. **结论**：净化**只撤了分支**，托管侧旧对象仍匿名可下 ⇒ 净化**未完成**。
3. **待办（按急迫度）**：轮换清单（每类凭据的条数）→ 删仓重建/Support 回收 → PII 合规记录。
