---
name: campaign-router
description: >-
  新目标 URL/域名的作战计划入口。触发：新目标、开始测试、怎么打、
  先从哪里入手、计划一下、作战计划、全扫一遍、kit_run、auto_campaign。
  已像网站/Java/PHP/盘口时用 kit_run，不知道栈时用 auto_campaign plan。
---

# Campaign Router — 智能作战路由器

> **本机核验（2026-10-21 彻底回滚后）**：完整的 231 个历史 `tools/ops/*.py` 中，**启用面 114/123 名、227/241 引用 = 94.2%**；9 个启用面缺口，13 个擅自写的实现已全部删除。归档面仍有 106 个 disabled/legacy 名字无文件。现在补的是高覆盖执行层，共 **125 个真实入口**。
>
> 真实可执行层：
> - `tools/ops/kit_run.py` — `check` / `list` / `run --kit web|recon` / `report`（web = whatweb + nuclei + ffuf；recon = subfinder + nmap + whatweb）
> - `tools/ops/auto_campaign.py` — `plan` 只读菜单；`run` 是 kit 的薄封装
> - `tools/ops/case_report.py`、`evidence_gate.py`、`object_matrix.py`、`scope_lint.py`
> - **125 个被现卡引用的真实 ops 名**（路由/探针 + 高频补链 + 兼容入口；目录内另有 28 个直达 symlink）
> - 底层 29 个纯标准库脚本：`.claude/skills/pentest-redteam/scripts/tools/`
>
> 运行前必须显式 `--scope`（不会自动把目标主机写成授权范围）：
>
> ```bash
> python3 tools/ops/kit_run.py check
> python3 tools/ops/kit_run.py run --kit web -u https://授权站 --case <案卷> --scope 授权域名
> python3 tools/ops/case_report.py --case <案卷>
> ```
>
其余 106 个 `tools/ops/*.py` 历史名仍无文件（全库 231 个唯一名，125 个已实现，1,264/1,539 处引用 = 82.1%；**启用卡 114/123 名、227/241 引用 = 94.2%**，9 个缺口）；菜单当“能力索引”读，执行前先 `python3 tools/ops/coverage_gate.py --active --strict` 或 `ls`，不存在就用现有适配器/二进制替代，禁止硬跑。

## 触发条件

用户给出一个新目标（URL/域名），且需要决定"用哪些工具/怎么打"时使用。
关键词：新目标、开始测试、怎么打、先从哪里入手、计划一下、作战计划、全扫一遍。

**成套入口**（散装探针的顺序+交接）：

```
tools/ops/kit_run.py
```

```bash
python3 tools/ops/kit_run.py list
python3 tools/ops/kit_run.py run --kit web -u https://授权站 --case <案卷> --scope 授权域名
```

`auto_campaign.py` 仍是指纹菜单；已经像网站/Java/PHP/盘口时用 kit，不要 31 个工具平铺。

## 核心工具（菜单）

```
tools/ops/auto_campaign.py
```

**菜单**（指纹 → 并列工具，不交接）。不知道栈时用。已经像网站/Java/PHP/盘口时改用上面的 kit_run。

## 立即执行步骤

### 第 0 步：军械库检索（强制，先于任何工具）

```bash
python3 /root/.hermes/arsenal/skill_find.py "<目标指纹/症状>" --top 8
```

`[D]` 卡按返回的 `load:` 行加载：`skill_view(name='<目录卡>', file_path='references/legacy/<卡名>.md')`。  

**已知产品/版本/CVE 时加查漏洞库**：

```bash
vuln_find "<产品 版本/CVE/未授权/RCE>" --top 8
```

`[POC]` 先读 `read:` 的 README/analysis，确认前置条件再执行；不要把 PoC 当通用 RCE。

缺工具现场补，不要停：`tool_get --check` → `tool_get <name>`；装完 `command -v` 验证。

先确认有没有现成打法、前置条件和脚本，再决定 `kit_run` / `auto_campaign`；禁止因为常驻索引里没有就自己重写。

### 第 1 步：生成作战计划（只读，1-5 秒）

```bash
python3 tools/ops/auto_campaign.py plan -d <目标域名>
```

可选参数：
- `--admin <URL>`：已知后台地址（跳过猜测）
- `--case <案卷名>`：输出到 `/root/cases/<案卷名>/`（与 case_ledger / kit_run 一致）

输出：
- 5 个阶段的工具列表（Phase 0 侦察 → 1 绕过 → 2 漏洞 → 3 接管 → 4 社工）
- 每个工具的触发原因 + 完整命令
- 目标指纹摘要（CDN/WAF/技术栈/功能模块）

### 第 2 步：执行（可选，自动运行全链）

```bash
# 全部执行
python3 tools/ops/auto_campaign.py run -d <目标域名>

# 只执行侦察阶段
python3 tools/ops/auto_campaign.py run -d <目标域名> --phases 0

# 执行侦察+绕过
python3 tools/ops/auto_campaign.py run -d <目标域名> --phases 0,1

# 先预览再执行（dry-run）
python3 tools/ops/auto_campaign.py run -d <目标域名> --dry-run

# 绑定现有案卷
python3 tools/ops/auto_campaign.py run -d <目标域名> --case wldzylbot_20260810
```

## 工具激活规则（指纹 → 工具）

| 指纹特征 | 激活工具 |
|---------------------|--------------------------------------------------------------|
| 任何目标 | osint_recon + test_subdomain_enum + js_secret_hunter + dirbrute_probe + nday_route + jwt_gql_probe + 1day_nuclei |
| Cloudflare/CDN | origin_recon + cf_backup_bypass + ip_whitelist_bypass |
| 后台 403/IP 白名单 | ip_whitelist_bypass（全 7 个向量） |
| 博彩站 | yudao_appapi_probe + port_admin_scan + tg_cmd_enum + api_dispatcher + logic_vuln + ws_probe + stored_xss + agent_probe + social_engineer |
| Java/Spring | actuator_probe + fastjson_probe + java_web_surface_probe（含 cnoa 国产 OA 指纹）；heapdump 可达或已有 hprof → **立刻** heap_cred_scan（蓝鸟蜘蛛） |
| 通达/泛微/用友/致远 | java_web `--stack cnoa` + Playbook `docs/playbooks/用友与致远OA手法.md` |
| CF/CDN 缓存头 | `cache_poison_probe.py` → `web-cache-poisoning` |
| 支付且像 USDT | `usdt_attr_hijack.py chain-scan`（只读）并行 bind-dup |
| 盘口 IDOR 阴 | `ato_reset_withdraw_probe.py`（任意 code + BOLA + 提现三件套，自控号） |
| TG 云控 `main.wasm` / 掩码票 | `tg_cloud_panel_probe` 第四族 + `jwt_gql_probe --token 掩码票` |
| 案卷有 Chrome.rar / cookies.sqlite / fingerprint.json | `has_browser_loot` → `from-case --url`（分诊 + 整包回放授权 URL）；活会话再 `session_import` |
| 点名 PwnKit / GodPotato / Log4Shell / ADCS ESC / shell.zip 手法 | `hypothesis_route.py --signal` → `shell包红队手法.md`（不部署 opus-injector） |
| Claude/Codex 拒答、助手没身份、要部署 CLAUDE.md | **manual**：`se_inject.py` 身份注入版已按操作员要求删除；不提供替代注入器，走官方通道或手工配置 |
| Harbor / 容器仓库 | `nday_route`（指纹 `has_harbor`） |
| Jeecg/Shiro/Druid | java_web_surface_probe → 对应手法卡（Shiro 默认做 L2 弱密钥碰撞） |
| ThinkPHP / PHP | thinkphp_surface_probe（默认 Client-IP 差分 + `.env`；`--no-probe-ip-header` 才关） |
| TP3 README / `ApiUserFenxiao` / `chk_update` / 剪贴板劫持 | `tp3_fenxiao_probe.py`（禁止 message_delete OR；WAF 拦 TP5 不算结案） |
| XXL-JOB / `:9997` / `GLUE_SHELL` | `xxljob_admin_probe.py`（登录认 Cookie/302/JSON；授权内 GLUE 直接做） |
| 标题「TG号码管理」/ `/export/download/` | `tg_number_admin_probe.py`（弱口+只读头；改密/百万拖号先问） |
| 宝塔/PMA / 博彩 PHP | panel_surface_probe + port_admin_scan |
| Java 旁注 Redis | redis_unauth_probe（INFO + captcha 键名） |
| NGINX/OpenResty | nginx_rift_probe（CVE-2026-42945 版本/改写面；默认不打 RCE） |
| 有支付功能 | `pay_matrix`；PHP/`composer.json` 先 `sensitive_dir_dump` 抽商户钥 |
| `/dj.svg` `use_balance` | 交接 `dujiao-next-1yuan-pay`（勿 acg-faka） |
| `acg.js` / `shared_id` | `acg_probe` |
| `dujiaoka` / `detail-order-sn` | `faka-card-shop-pentest` + 假支付合法签 |
| 有代理体系 | agent_probe（BOLA + JWT 提权）+ social_engineer_agent |
| 有上传/URL预览 | ssrf_probe |
| CDN/OSS | bucket_probe |
| WAF | waf_sqli_bypass |
| 数字人 / `ref_sequence` / `/inference` / Img2Avatar / FancyTalk | `digitalhuman_inference_probe.py`（先 quote 反引号，`;id` 假阴） |
| LiteLLM / Langflow / `/v1/models` | llm_surface_probe → LiteLLM/Langflow 专卡（不做越狱） |

上表文件名对应本库路径（蒸馏认 `tools/ops/*.py`）：

```bash
python3 tools/ops/test_subdomain_enum.py --help
python3 tools/ops/dirbrute_probe.py --help
python3 tools/ops/fastjson_probe.py --help
python3 tools/ops/redis_unauth_probe.py --help
python3 tools/ops/bucket_probe.py --help
python3 tools/ops/ip_whitelist_bypass.py --help
python3 tools/ops/waf_sqli_bypass.py --help
```

## 重要说明

- `auto_campaign.py plan` 是**只读操作**，不会发送任何攻击性请求
- 只有 `run` 命令才真正调用子工具
- 指纹识别约需 3-8 秒（HTTP 探测），之后立即输出计划
- 每个阶段可独立执行（`--phases 0,1,2` 等）
- 所有工具输出都写入 `exports/bot-recovery/<domain>_auto/`

## 与其他 Skill 的关系

- 业务站/后台/API 分流总卡 → `docs/playbooks/打网站手法.md`（设备洞降权）
- 只丢工具名/手法名 → `docs/playbooks/安全作业关键词分流手法.md`
- 无专用栈 → **先** `strike_probe.py`（S1–S8）再 `核心Web漏洞面作业手法.md` + `authz-probe`
- 发现 `/actuator` → 切换到 `spring-actuator-cloud-takeover` Skill
- 发现 `/actuator/heapdump` 或案卷 `.hprof` → **立刻** `heapdump-credential-hunter` / `heap_cred_scan.py`（不问蓝鸟）
- 发现支付回调 → 切换到 `payment-callback-forgery` Skill 
- 收工 / 写结案 → `evidence_gate.py --from-status` + `object_matrix check`（口头结论对测绘原文，禁止 STATUS 自证）
- 需要社工 → `tg-account-library` + `social_engineer_agent.py`（技术面穷尽 + 入场券）
- 号库/session 投递 → `tg-account-library`
- 博彩站/赌博台 → 先 `docs/playbooks/博彩站打法分流手法.md`，细链 `博彩站完整杀伤链.md`
- 白标/芋道 TMA/`sk_encrypt`/Qzino → `yudao_appapi_probe.py` + `白标博彩家族与加密API分流.md`
- IP 白名单挡住 → `docs/playbooks/IP白名单绕过杀伤链.md`


---

## 外部库增量（2026-10-11 分享包）

## 目标分档（接单第一步，30 秒）

**不是所有目标都配全量管线。** 信息收集永远是打站第一步——背景调查做透，
才有一发子弹找弱点射击；两档的区别只在后续推进的厚度：

- **简单站 → 轻量快打档**：无 WAF/CDN、单体、无纵深、面直接（小商城/发卡站/单后台/成品 CMS）。
  路径 = 信息收集 → 指纹 → 直奔最弱面（未授权 → 默认口令 → 已知 CVE → 上传点）→ 一发 RCE 拿下。
  一轮内解决；不平铺探针菜单、不排长管线、不上矩阵/账本仪式。
- **复杂站 → 全量档**：WAF/CDN/源站隐藏、Java/微服务/多租户、资金面、内网、环环相扣。
  才上完整管线：面重建、分流、对象矩阵、假设账本、长跑纪律——
  领土大出错点就多，系统化是在管理复杂度，不是仪式。

**判不准先按简单站快打一轮**：打不动再升级全量，比全量空转便宜。
快打省的是仪式，不省的是两样：背景调查的扎实度、「开枪必须真响」（真 shell/控制权才算拿下）。
