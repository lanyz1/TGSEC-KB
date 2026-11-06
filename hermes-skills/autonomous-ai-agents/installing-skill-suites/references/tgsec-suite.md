# TGSEC 渗透套件 (TGSEC-Qtzuuz)

安全渗透知识库 + 多框架 AI 技能包。合法用途：授权渗透 / CTF / 学术 / 防护研究。

## 关键事实
- **正确仓库：** `https://github.com/Yufeifeio/TGSEC-Qtzuuz`（`Qtzuuz` 双 z）。
- **仓内安装脚本/README 写的是** `lanyz1/TGSEC-Qtzuu`（单 z、错作者）——该仓库不存在，照抄必 404。克隆/安装一律用上面的正确 URL。
- **安装入口：** `scripts/install-linux.sh` clone 到 `~/security-suite` 后跑 `bootstrap.sh --force`。
- **记忆覆盖点：** `ai-config/hermes/setup.sh` 把 `USER.payload.md` / `MEMORY.payload.md` 覆盖到 `~/.hermes/memories/USER.md` / `MEMORY.md`（渗透人设）。
- **技能落点：** `hermes-skills/` → `~/.hermes/skills/security/`（overlay，不删私有技能），约 15 个技能。
- **知识正文：** `domains/`，入口 `START.md` → `AGENTS.md` → `ROUTING.md` → `MASTER.md`。

## 安全安装（跳过记忆覆盖）
```bash
git clone --depth 1 https://github.com/Yufeifeio/TGSEC-Qtzuuz.git ~/security-suite
cd ~/security-suite
mv ai-config/hermes/setup.sh ai-config/hermes/setup.sh.DISABLED   # 跳过记忆覆盖
bash scripts/bootstrap.sh --force
mv ai-config/hermes/setup.sh.DISABLED ai-config/hermes/setup.sh   # 恢复
```

## 更新
```bash
cd ~/security-suite && git pull
# 再禁用 setup.sh，跑 bootstrap --force（同安装）
```

## 授权边界（硬性，来自仓内 AGENTS.md）
- 活靶 ACT 前确认：SRC / Bug Bounty / 自有资产 / 书面授权 / CTF 之一。
- 禁止未授权打公网；禁止输入 URL 就自动伪造授权。
