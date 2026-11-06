# 思念maxskill 吸收明细 (2026-10-02)

## 三重对比口径
| 项 | 数字 |
|---|---|
| 包内 | 138 SKILL.md(111,484 行实扫) / 690 文件 / 95 脚本 |
| 本地同名(吸收前) | 70 |
| 测绘引擎知识包同源(B组) | 14 — 不导入 |
| 判定真空白 | 47 安全 + 7 工具 = 54 卡导入 |
| 本地同名(吸收后) | 124 |

## 54 卡全清单(→ 镜像分类)
### 旗舰 3
sinian-omnipotent(18,072行/74章) · pentest-execution · tgsec-suite

### 01-web渗透 (23)
captcha · puzzle-slider-captcha-bypass · frontend-js-api-recon · frontend-crypto-transport-reverse · java-deserialization-jndi · web-rce · web-sec · web-error-oracles · web-security-hardening · hosting-control-panel-pentest · resource-panel-unauth · aliyun-shield-waf-bypass · hfs2-0day-rce · 0day-exploit-library · credential-hunter-v6 · payment-gate-ladder-probing · payment-gateway-api · gambling-platform-pentest · gambling-source-audit · php-vendor-shell-family-attack · tg-gambling-asset-recon

### 其余域 (17)
- 02-逆向破解: reverse-skill
- 03-网络渗透: fofa-mapping-unauth-services · host-reachability-verification
- 04-云安全: ghostlock-kernel-exploit · linux-kernel-exploitation
- 06-密码OSINT社工: crypto-fund-flow-and-key-audit
- 07-恶意软件取证: attacker-eviction-hardening · attacker-infrastructure-pentest
- 08-红队C2: black-cat-redteam · hama-apt-redteam · redteam-infra-opsec
- 09-综合辅助: about-security · hack-skills · secatlas · arsenal-inventory · security-kb-ingest · engagement-scope-gating · proxy-pool-rotation · web3-dev-services
- 10-AI与Agent基建: stopen · cyberstrike-ai · claude-bughunter
- 11-研发工程: porting-pentest-mechanisms-to-go

### 工具 7
archive-extraction · cursor-agent-soul-port · hermes-localization · installing-skill-suites · agent-backup-restore · rebranding-open-source-tool · project-rebranding

## 吸收后验证数字
- 本地库: 1,119 卡 / 7,696 文件 / 726 脚本(gen_docs 口径)
- organize: 15 分类全绿 · 0 未分类 · 0 待清理
- D 盘镜像: 各分类目录已就位(09-综合辅助 185 卡含 sinian-omnipotent 等)

## 未导入原因清单(留在镜像)
### B 组 14: 与测绘引擎知识包同源(shizhan-pack 已有)
account-opening-security · active-directory-lateral-movement · ai-llm-attack-surface · anti-forensics · cloud-security-pentesting · data-exfiltration · password-attacks-credential-access · pentest-redteam · persistence-mechanisms · post-exploitation-framework · supply-chain-attacks · telegram-mini-app-bot-security · unauthorized-access-common-services · windows-privilege-escalation

### 厚卡 8: 本地有同名但包内版远厚(镜像可回收)
| 卡 | 包内行数 | 本地行数 |
|---|---|---|
| wireless-security | 5,422 | 112 |
| linux-privilege-escalation | 3,245 | 115 |
| social-engineering-framework | 3,012 | 103 |
| reverse-engineering | 2,720 | 16 |
| exploit-development-framework | 2,161 | 103 |
| iot-security-testing | 2,013 | 117 |
| isp-traffic-hijacking | 1,953 | 106 |
| dns-pollution-hijacking | 1,321 | 222 |

### 保留事项
- 3 个源包截断文档(已加缺口注释): 见 pentest-execution/references/
- about-security/hack-skills/secatlas 为外部仓库索引(指向思念服务器), 仅索引无内容
- 4 个旧名残留已移至: `D:\博彩通杀\技能库\_deprecated\旧名残留-20261002\`
