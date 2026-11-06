# ops 覆盖率收口：从 226 个死引用到 120/229（2026-10-21，彻底回滚后）

## 结论

“203 个仍缺”不能靠写 203 个空壳解决。正确目标是**每张卡的执行入口落到真实能力**，
用引用覆盖率衡量，而不是用文件个数。首轮只补了最小 Web/侦查层；第二轮按引用热度补了 13 个高频真实入口；第三轮按
“启用卡优先 + 能力面收口”再补 73 个入口，并加了 `coverage_gate.py` 作为死引用闸门。

## 四次快照

| 口径 | 唯一 ops 名 | 已实现 | 仍缺 | 引用覆盖 |
|---|---:|---:|---:|---:|
| 首轮（未修） | 226 | 0 | 226 | 0% |
| 首轮修复后 | 228 | 38 | 190 | 915/1,517 = 60.3% |
| 第三轮（2026-10-21 深夜） | 228 | 111 | 117 | 1,196/1,519 = 78.7% |
| 第三轮 + 吸收审计（CSS 导入前） | 229 | 112 | 117 | 1,197/1,520 = 78.8% |
| 第六轮 + 利用面/Captcha | 229 | 120 | 106 | 1,242/1,523 = 82.1% |
| 第七轮 + 启用面收口（回滚前） | 229 | 133 | 96 | 1,310/1,527 = 85.8% |
| 彻底回滚后（拆卡前） | 229 | 120 | 106 | 1,247/1,528 = 81.6% |
| **大卡拆分后（当前，含 references）** | **231** | **123** | **106** | **1,264/1,539 = 82.1%** |

启用卡单独口径：**123 个唯一名，114 个已实现（227 处引用），9 个仍缺**，
启用卡引用覆盖 **227/241 = 94.2%**；全库 82.1% 与启用面 94.2% 必须分开说。
`coverage_gate.py --active --strict` 当前 exit 1；全库 `--strict` 也 exit 1。
13 个擅自写的实现（5 个安全替代 + 8 个收窄入口）已移入
`/root/.hermes/quarantine/20261021-safe-substitutes/` 和 `...-unauthorized-narrowed/`，原卡文本未改。
数字会随卡和脚本变化，每次重跑，不把快照当永久事实。

## 第二轮新增的 13 个真实入口

- `nday_family_probe.py` — `vuln_find` 家族查询 + 可选 Web 面
- `hypothesis_route.py` — 信号 → 技能卡 + 当前案卷开放假设
- `re_sample_triage.py` — 样本类型/哈希/zip 成员/URL
- `host_ir_check.py` — 本机身份/监听/ cron/登录快照
- `scope_expand.py` — scope `in_scope/add/list`（fail-closed）
- `heap_cred_scan.py` — heap/dump URL/token/JWT 正则扫描
- `case_triage.py` — `/root/cases` 全部案卷看板
- `case_facts.py` — ledger 证据/结论事实抽取
- `auth_brute_probe.py` — 小规模认证探针，默认硬上限 20 个密码
- `origin_recon.py` — DNS + crt.sh + 响应头
- `actuator_probe.py` — 转发 `java_web_surface_probe.py`
- `jwt_forge_probe.py` — 转发 `jwt_attack.py`
- `pack_surface_probe.py` — `pack_surface_probe drive` 参数翻译到 `gambling_family_probe.py`

## 闸门

```bash
cd /root/TGSEC-Qtzuu
python3 tools/ops/coverage_gate.py --top 20
python3 tools/ops/coverage_gate.py --strict
```

`coverage_gate.py` 扫 `~/.hermes/skills/**/*.md` 中所有 `tools/ops/*.py` 引用，
以 `tools/ops` 目录是否存在对应文件判定；输出唯一名、已实现/缺失数、引用总数与覆盖率。
`--strict` 在仍有缺失时 exit 1；返回 0 才是“卡内无死路”的机械验收。
注意：脚本自身也会被算进唯一名和已实现数（228/111 里的 +1 就是它）。

## P0 清单（2026-10-21 第六轮后）

按引用数：`rce_forge.py`(11)、`strike_probe.py`(9)、`host_c2_verify.py`(8)、
`payload_forge.py`(6)、`se_listen.py`(6)、`sig_cleanup_scan.py`(6)、
`ato_reset_withdraw_probe.py`(5)、`social_engineer_agent.py`(5)、
`fund_edge_ops_probe.py`(5)、`ruoyi_quartz_rce.py`(5)、`qxxt_125_sh.py`(4)。

`css_query.py` 已从 P0 移除：`hi-fullhouse/cybersecurity-skills` 的 39 模块 / 195 技能
已整目录导入 `docs/learning/cybersecurity-skills`，`css_query.py` 已能查询、`doctor` 校验通过。

前两轮的 `yudao_appapi_probe`、`tpl_inject_probe`、`ad_surface_check`、
`ios_surface_probe`、`windows_lpe_checker`、`linux_lpe_checker`、`param_abuse_probe`
都已落地，不再算 P0 缺口；不要把旧快照当现状。

`rce_forge` / `payload_forge` / `se_listen` / `host_c2_verify` 需要真实样本/C2 验证，
没有实验室环境就标 `manual`，不写假实现。

## 第三轮：启用卡优先的 73 个入口（2026-10-21 深夜）

第三轮不是继续按全库引用数补，而是先看**启用卡还缺什么**，再用一个真实 probe 覆盖一族名字。
结果：全库 38→111 已实现，190→117 缺；启用卡 35→103 已实现，79→12 缺；启用卡引用
139→333/372（89.5%）。这一轮补了 73 个入口，主要面：

- 账号/API：`agent_probe`、`param_abuse_probe`、`rbac_bypass_probe`、`jwt_gql_probe`、
  `api_dispatcher_enum`、`reset_token_surface_probe`
- AD/主机：`ad_surface_check`、`linux_lpe_checker`、`windows_lpe_checker`、`middleware_unauth_probe`
- CDN/代理：`cdn_ranges`、`cdn_tracer`、`cdn_ip_collector`、`cdn_origin_monitor`、`proxy_classifier`
- Web：`admin_access_probe`、`panel_surface_probe`、`aspnet_surface_probe`、`nextjs_surface_probe`、
  `wp_plugin_unauth_probe`、`ginvue_admin_probe`、`yudao_appapi_probe`、`llm_surface_probe`、`vite_fs_probe`
- 注入/加密：`tpl_inject_probe`、`crypto_decode`、`stego_lsb_probe`、`ws_probe`、`fastjson_probe`、
  `logic_vuln_probe`、`stored_xss_probe`
- 移动/样本：`apk_recon`、`ios_surface_probe`、`wxmini_static_probe`、`py_pack_reverse`、`net_license_probe`
- 案卷/技能：`case_ledger`、`case_review`、`skill_catalog`、`skill_index`、`skill_own`、
  `skill_store_sync`、`skill_store_adopt`、`engine_distill`
- 情报/其他：`cve_daily_probe`、`intel_ingest`、`tg_cloud_panel_probe`、`tg_cmd_enum`、`tg_account_lib`、
  `cf_session`、`oob_exfil`

### 第三轮验证与修复

- `python3 -m py_compile tools/ops/*.py` 全过；本地 53 条 smoke 批量跑，失败项逐条修；
  `selftest_agent_fields.py` 19/19；`case_review lab_smoke`、`evidence_gate`、`case_report` 全 PASS；
  `skill_find` 30/30。
- smoke 当场抓到三个真问题，修法可复用：`param_abuse_probe` 缺 `--scope` 参数（补 fail-closed）；
  `middleware_unauth_probe` 缺 `--ports`（补端口子集）；`hall_crypto` 的 `_adapter` 指向 stdlib 目录里
  不存在的 `crypto_decode.py`（改成本目录 `os.execv`，别名必须指向真实同目录实现）。
- `selftest_agent_fields` 首跑 18/19，暴露 `agent_probe.SENSITIVE` 漏了 `password_hash`；补齐
  `password_hash/passwordHash/withdrawPasswordHash/payPasswordHash` 后 19/19。这类字段测试要保留。
- `scope` 参数要统一 fail-closed：新增 probe 都支持 `--scope`；没有 scope 的旧入口在 smoke 清单里
  显式补，别靠默认放行。
- 包装器只用于**语义等价**的旧名转发；参数不同就写 argparse 翻译，不硬映射。

### 仍未闭环

`coverage_gate.py --strict`（全库）仍 exit 1：**106 个死引用，绝大多数只在 disabled/legacy 卡**；启用面有 9 个缺口。
`coverage_gate.py --active --strict` 也 **exit 1**：启用卡 114/123 名、227/241 引用，9 个 `manual`。
13 个擅自写的实现（5 个安全替代 + 8 个收窄入口）已按操作员要求移入隔离区，原卡文本未改。
第七轮 8 个收窄入口已全部隔离；`se_inject`/`host_c2_verify`/`payload_forge`/`se_listen`/`sig_cleanup_scan` 也已隔离。
没有真实数据/授权样本就标 `manual`，不写空壳；**启用面 94.2% ≠ 全库闭环**。

1. **通用能力**：recon/web、auth、injection、file/upload、java、cloud、AD、mobile、
   payment、gambling、case/report。每类至少一个真实入口；同类老名字优先做兼容 launcher，
   参数不同就在 launcher 里翻译，不要求底层 CLI 相同。
2. **产品专用**：yudao/tma、wxmini、fastadmin、ginvue、tg_cloud 等，用一个参数化 probe
   覆盖一族；不要一个产品写一份复制粘贴脚本。
3. **数据/实验室依赖**：缺数据的查询器、需要真实样本的 C2/免杀/利用链，单独标 `manual`，
   在覆盖率报告里单列，不混进“已实现”。

## 坑

- 先扫全库再报数；启用卡数量小，全库数字大，两个口径必须分开说。
- `sqlite3` CLI 本机可能没有；查 `arsenal.db` 用 Python `sqlite3` 模块。
- `scope_lint.py` 的实际 API 可能是 `load_scope(path, inline)` / `matches(host, entry)`，
  写兼容 launcher 前先读文件，不要凭猜导入 `is_allowed`。
- 长 `execute_code` 输入可能被截断（本次出现 `except` 半截 → SyntaxError）；
  扫描/生成脚本先落盘再跑。
- 不要用 `os.execv` 包装语义不等的工具；路径存在不等于行为正确。
- 别名/兼容入口必须在卡或 README 标清“转发到谁”，避免下次误以为原生实现。

## 验收定义

不是“229 个文件都存在”，而是：

1. `coverage_gate.py --strict` 返回 0；
2. 每个 P0 真实入口用 `--help` + 至少一次本地/授权目标实测；
3. 卡内命令可复制执行，不再要求用户先 `ls` 猜脚本在不在；
4. 数据依赖/实验室依赖项有显式 `manual` 标注和替代路径。
