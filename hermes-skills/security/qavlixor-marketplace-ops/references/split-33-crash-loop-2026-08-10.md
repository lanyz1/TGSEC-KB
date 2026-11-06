## 部署中断 → crash loop 恢复流程（2026-08-10 实录）
**现象**：部署命令被中断（deploy.py 被杀）→ 服务器 tar 解压半程代码损坏 → PM2 4 实例全部 `waiting restart`（restarts 100+，crash loop）→ Cloudflare 502。**任何"部署进行中被掐断"后用户报 502 = 先查 pm2 jlist 的 status/restarts，别猜攻击**。
**恢复（手动重部署，deploy.py 可能因"nothing to commit"卡住时用）**：
```python
# ① 打包（Windows Python 子进程无 gzip！用 gzip 模块）
raw = subprocess.run("git archive --format=tar HEAD", shell=True, capture_output=True, check=True).stdout
with open("qav-deploy.tar.gz","wb") as f:
    with gzip.GzipFile(fileobj=f, mode="wb", compresslevel=6) as gz: gz.write(raw)
# ② paramiko 上传 → ③ 服务器：tar xzf 覆盖解压 + db push + next build --no-lint（看日志确认 87/87 页面完成）
# ④ pm2 restart ×2 + curl 200 探测 + 外网 https://qavlixor.com 200 确认
```
**教训**：①部署命令跑完前（~100s）不可中断；②deploy.py git commit 步骤已加容错（nothing to commit 不再 exit 1 卡部署）；③deploy.py 的 db push 已去掉 `--skip-generate`（**schema 加新字段后服务器 Prisma Client 必须重新 generate，否则新字段的 update/findUnique 静默失败**——本会话忘记密码 token 落库 NO 就是这个原因，手动 `pnpm prisma generate` + `pm2 restart` 解决）。

