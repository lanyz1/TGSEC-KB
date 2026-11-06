<!-- archived from /root/.hermes/skills/security/security-skill-library/SKILL.md on 2026-10-21 -->

---
name: security-skill-library
description: 触发词:整理技能库,更新技能库,技能整理,组织安全技能。维护 D:\博彩通杀\技能库\ 技能镜像与实战案例集。
---

> 归档卡：原目录 `/root/.hermes/skills/security/security-skill-library`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/security-skill-library/…')`，不要相对 `references/legacy/` 解析。

# Security Skill Library (安全技能库整理)

用户在项目目录(如 `D:\博彩通杀\`)维护一份 Hermes security 技能的全量分类镜像 + 实战情报文档。已建成:

- `D:\博彩通杀\技能库\` — 228 个 security 技能按 9 大分类镜像(927 文件,271 脚本;2026-09-07 吸收测绘引擎知识包 +23)
- `D:\博彩通杀\实战案例集.md` — 从长期记忆提炼的结构化实战情报(10 章:v2rayN陷阱/fndata/EMSHOP/RTG/Gambit/FairGo/m9600/UMI/发卡采集/方法论)
- `D:\博彩通杀\技能库\会话沉淀对照.md` — 全历史会话 → 技能沉淀对照(2026-09 建立)
- 来源: `（朋友 Hermes 工作区路径，本库对应 tools/ops/）skills/security/`(228 个技能目录)

## 重新生成(幂等,可反复跑)

```bash
cd "D:\博彩通杀\技能库\_index"
python organize_skills.py   # 按 CATEGORIES 映射复制技能→分类目录, 输出 skills_index.json
python gen_docs.py          # 从 JSON 生成 README.md / 技能明细.md / 技能库统计.md
```

- `organize_skills.py` 顶部的 `CATEGORIES` dict 是**唯一分类事实源**: 新增技能必须补映射,否则落入"未分类"警告(脚本会打印 ⚠️)
- 脚本内 `SRC` 指向 skills/security,`DST` 指向项目技能库
- 技能通用结构: `SKILL.md`(frontmatter: name/description/Trigger) + `scripts/` + `references/` + `templates/`(可选)

## 9 大分类 (taxonomy)

| 目录 | 数量 | 范围 |
|------|------|------|
| 01-web渗透 | 72 | SQLi/XSS/SSRF/SSTI/XXE/GraphQL/SPA/SaaS/卡密商城/赌场/API/TG bot/TG小程序/Vol.Core/停车平台/AI agent运行时 |
| 02-逆向破解 | 32 | EXE/Nuitka/fndata/注册机/脱壳/Go/.NET/Python/iOS/固件/Flutter/Dart/Auto.js/docker提取 |
| 03-网络渗透 | 14 | 端口/提权/横向/持久化/隧道/AD/后门 |
| 04-云安全 | 10 | AWS/Azure/GCP/K8s/Docker/CF源站绕过/空间测绘 |
| 05-移动硬件无线 | 17 | 安卓/WiFi/NFC/RF/USB/车/无人机/ICS/SCADA/VoIP |
| 06-密码OSINT社工 | 15 | 密码破解/OSINT/钓鱼/隐写/加密货币/混币/钱包 |
| 07-恶意软件取证 | 13 | 免杀/勒索/rootkit/取证/漏洞研究 |
| 08-红队C2 | 10 | C2/Shellcode/ROP/浏览器利用/游戏破解/零信任 |
| 09-综合辅助 | 17 | 技能安装器/态势评估/回退/报告生成/作战指挥(cyber-ops)/复盘回写(ops-review)/情报摄入(intel-ingest)/COD运维/TG数据机器人/跑分 |
注: 2026-09 补齐 43 个历史未分类技能映射,新增 ai-agent-runtime-pentest → 01-web渗透。

## Workflow

1. 读 `organize_skills.py` 的 `CATEGORIES` 确认现有映射
2. 新增技能时在 `CATEGORIES` 加行 → 重跑 `organize_skills.py`,检查 ⚠️ 未分类输出
3. 重跑 `gen_docs.py` 刷新三个索引文档
4. 若记忆/会话有新实战情报: 追加到 `D:\博彩通杀\实战案例集.md` 对应章节(不新建章节,除非新主题)

## Pitfalls

- Windows 中文目录名(`01-web渗透`)在 README 相对链接中正常工作,不要为了"规范"改成英文
- git-bash 路径用 `/d/博彩通杀/...`;Python 脚本内用 `D:\博彩通杀\...`
- description 提取只读 SKILL.md frontmatter 前 2000 字符;触发词在 `Trigger:` 之后
- 源技能多为用户安装的"绫波丽101技能"zip → USER-OWNED,不可 patch;仅 curator 创建的(如 fndata-auth-bypass)可改
- 整理后主交付物是 README 总索引 + 实战案例集,用户看重实战情报胜于技能列表本身

## Overlaps known (交给 curator 合并)

> 2026-09 已合并: `cloudflare-origin-bypass` + `cloudflare-origin-discovery` → **`cloudflare-bypass`**(CF 家族总技,absorbed_into)。

windows-binary-cracking ≈ windows-binary-reversing ≈ windows-exe-cracking ≈ windows-exe-crack-methodology;cloudflare-bypass ≈ cloudflare-bypass;credential-stuffing ≈ online-credential-stuffing;white-label-casino-pentest ≈ white-label-pentest;evasion ≈ evasion-advanced;exploit-dev 系列 3 个。


---

## 外部库增量（2026-10-11 分享包）

## 报告 → 技能沉淀(一键流程,2026-09-25 起)

输入=一份渗透/审计报告;输出=新卡(或家族卡回填) + 镜像 + 索引 + 三份文档 + 五项校验。
脚本 `scripts/report_to_skill_sync.py`(**在技能卡目录**,不在 `_index`)。

```bash
S="C:/Users/Administrator/AppData/Local/hermes/profiles/123/skills/security/security-skill-library/scripts"
python3 "$S/report_to_skill_sync.py" \
  --skill "新卡名:01-web渗透:一行备注" \
  --file  "security/已有卡/SKILL.md:01-web渗透/已有卡/SKILL.md" \
  --verify-name 新卡名
```

六步(**顺序不能换**):

| 步 | 动作 | 漏了会怎样 |
|---|---|---|
| ① | 源卡存在性 + 截断标记自检 | 把半截内容镜像出去 |
| ② | **登记 `organize_skills.py` CATEGORIES**(缺失自动插入 + 写 .bak) | 下次全库跑把镜像当「陈旧」清掉 |
| ③ | 调 `mirror_one_skill.py` **精准镜像单卡** | 手写索引 → 格式漂移(见下) |
| ④ | 回填**已有卡**的更新文件(含 references) | 新知识留在源侧,镜像侧还是旧文 |
| ⑤ | `gen_docs.py` 重建三份文档 | README/明细/统计与实际不符 |
| ⑥ | 校验:索引条目 / 技能明细 / CATEGORIES **+ 索引↔镜像一致性 + 全库截断扫描** | 交出去自己都没核过 |

**判据:末行必须是 `结果: 全部通过`**;出现 `x` 就是真失败,别当噪音跳过。

★ **能用脚本就用脚本,不要手点这六步**:手工跑必漏 ⑥(索引↔镜像一致性 + 全库截断扫描),
而且单卡镜像容易只跑一半(漏回填已有卡、漏 `gen_docs.py`)。只有输入形态套不进脚本时才手工补,补完自己把 ⑥ 补上。

### 独立体检器 `scripts/verify_skill_sync.py`（7 项,可对**任意已有卡**跑）

6 步里的 ⑥ 只在同步流程内部生效;要体检历史卡(或回填后单独复核)用这个独立件:

```bash
S="C:/Users/Administrator/AppData/Local/hermes/profiles/123/skills/security/security-skill-library/scripts"
python3 "$S/verify_skill_sync.py" --skill "卡名:01-web渗透"                          # 新卡: 7 项全量
python3 "$S/verify_skill_sync.py" --file "security/旧卡/x.md:01-web渗透/旧卡/x.md"   # 回填: 单文件一致
python3 "$S/verify_skill_sync.py" --selftest                                        # 离线自证(合成样本+6 种破坏场景)
```

七项: C1 frontmatter/正文长度 · C2 未声明截断标记(`SKILL-GAP` 声明的豁免) · C3 同目录唯一(create 未归位/半张卡) ·
C4 附件指针(孤儿附件) · C5 源↔镜像逐文件 SHA256 · C6 索引条目与分类 · C7 CATEGORIES 登记。
判据同为末行 `结果: 全部通过`;exit 0/1。★ 实测对 5 张卡跑当场揪出 2 个孤儿附件(`mock_fpm.py`、`jingzhe-case.md`) ——
交付前对**本次碰过的所有卡**各跑一遍。

**输入侧拆解方法(切几刀、切到哪、哪张新开哪张回填)见 `references/report-decomposition.md`。**

### 带 `scripts/` 的卡:交付门槛是**本地跑通**,不是 `py_compile`

新卡(或回填卡)里凡带请求器/探测器/gadget 脚本,**验收动作 = 对本地靶场跑通全部子命令**;
`py_compile` 过、`--help` 能出提示页不算。没有现成靶场就现场造一个(零外部目标,一小时内):

1. 便携运行时装 D 盘、不改系统 PATH、不动系统环境(实测 PHP:windows.php.net 的 archives 目录,
   解压到 `D:/pentools/php/<ver>`;`php.ini` 按脚本需要开扩展,如 `pdo_sqlite`)。
2. 写**单文件模拟器**复刻目标的**语义**而不是外观:路由与参数合并方式(框架会不会把 JSON body 解进 params)、
   WAF 的**匹配面**(只查 URI+查询串?还是含 body?)、限制项(`disable_functions`、散落 `.php` 是否 404)。
3. 逐子命令跑,断言**对照关系**(合法形态 200 / 非法形态 403、执行是否有回显、错误语义是否与真机一致),
   不是只看「有回显」。
4. 模拟器存回卡里 `scripts/mock-*.<ext>`,并在 SKILL.md「参考」段写一行**怎么起**(端口、docroot、要建哪些目录),
   下次回归或演练 payload 不必再碰真目标。

真跑的价值在于**只有跑才会暴露的 bug**:选项解析位置(全局选项写在子命令之后被拒)、
响应自动分类误判 —— 后者的规则是**拦截页判据必须三条并列**(小体积 ≲4KB + HTML/403 + 特征短语):
只看关键词会把「读文件/执行回显」的内容误判成拦截页(读一个 WAF 相关文件就中),
于是脚本报"被拦"而你以为链路死了。这两类 bug 静态检查一律查不出来,却直接决定脚本能不能用。

### 分流判据(建新卡还是回填家族卡)

| | 建新卡 | 回填家族卡 |
|---|---|---|
| 内容 | 一条**链路/攻击面家族**(目标可横向替换) | 单点新知识、新判据、新实测数字 |
| 例 | 后台→密钥面→裸端口→DB/MinIO→云AK 五层链 | 「验证码服务端不校验」→ 挂若依总纲 4.x 段 |
| 落点 | `security/<新名>/` + `references/NN-*.md` | 已有 SKILL.md 对应小节 + 该卡 references/ |
| 回挂 | 卡内「关联」表指向家族卡 | 家族卡「参考」段增一行指针 |

报告里的**负面结论也要落卡**(判据必须是响应原文,如 `EL1007E Property or field 'dat…`),不能写「没找到」。

### 实测坑(都踩过)

- ★ **必须走 `mirror_one_skill.py`,不要自己 `json.dump` 索引**:手写不排序、缩进不同 → 索引格式漂移
  (实测被写成 388 条 indent=1 + 未排序)。镜像脚本才保证 indent=2 + 按 `(category,name)` 排序。
- **索引↔镜像一致性要单独查**:索引会**漂移**(镜像有目录、索引没条目)。实测补回 3 张
  (`api-param-name-discovery`/`captcha-ocr`/`ginvue-admin-reward`) —— 当时 README 报 386 而镜像里已有 389 张。
- **截断扫描要用严格正则** `HERMES-CONTEXT-COMPRESSION:\s*[\d,]+ of [\d,]+ chars omitted`,
  并**排除扫描器自身 + 记录这条教训的 SKILL.md**,否则「文档里描述标记的那句话」会自命中(实测 3 误报 vs 2 真命中)。
- **真截断实例**:`ip-ban-bypass/references/waf-content-type-bypass.md`(682B,只剩「现象」+ 半张矩阵) —
  扫描器报 x 时**先看字节数**:小文件 + 标记 = 正文全丢,不是误报。
- **缺口只有两条出路:补全,或显式声明**(声明也算交付,但必须写明「剩什么能用、什么不可引用」)。
  声明格式:文首写「已知缺口」并加 ASCII 标记 `SKILL-GAP` → 扫描器把它列进
  「已声明缺口 N 处(不计失败)」,判据不会永久变红;带压缩标记又**无**声明的才是真失败。
  ⚠️ 标记必须用 `SKILL-GAP` 这类 ASCII 词:中文「已知缺口」会在正文里撞词(实测 qavlixor 附件误命中 7 处)。
- **孤儿附件要顺手挂回自家卡**:实测 `waf-content-type-bypass.md` 的 `references/` 文件在
  `ip-ban-bypass/SKILL.md` 里**一次都没被引用**(改完才发现)。建卡/改卡后 grep 一次附件名,别留隐形资产。
  ⇒ 现在有机器判据: `verify_skill_sync.py` 的 C4 会直接点名。同类实测: `jingzhe-case.md`(老案例文件被新文件
  取代后失去指针)、`mock_fpm.py`(脚本写进卡但正文没提)。
- ★ **`skill_manage` 一批多 op 是原子的:一个失败全批回滚**(含已经成功的 `write_file`)。
  实测一批里 `related_skills` 的 `old_string` 猜错 → 同批的 `references/*.md` **也没落地**。
  ⇒ 一批里别混「猜的 patch」和「重要的 write_file」;patch 前先 `read_file`/`grep` 拿准锚点原文。
- **`create` 把 SKILL.md 落在 `skills/<名>/`,不在 `skills/security/<名>/`** ⇒ 建完必须 `mv` 归位,
  否则库里出现「半张卡」(校验器 C3 直接报 `卡落在 skills 顶层`)。
- **`patch` 的 `new_string` 漏行 = 静默删内容**,没有冲突提示。实测把一条 pitfall 弄丢,靠复核才发现。
  ⇒ 改完立刻 `sed -n '/## §X/,/## §Y/p' <卡>/SKILL.md` 把整块打出来看,别只看 `success:true`。
- **YAML `description` 两条硬规则**:① 有长度上限(实测 287 chars 被拒 `Description is 287 chars (447 chars)`);
  ② 值含冒号/中文必须加双引号,否则 `YAML frontmatter parse e`。短中文描述(20~30 字)最稳。
- **报告结论要重判**:报告里的 ❌(「已穷尽/不可能/无法提权」)优先复核 —— 实测 `disable_functions` 那条结论就是错的
  (`extension` 走请求初始化阶段加载,不查函数禁用表 → 能拿真 OS 命令)。方法论: `references/report-decomposition.md` §5。
- 回填后**必须再跑一次 `--verify-name`**:镜像侧路径写错不会报错,只会静默不写。

## 外部资料(课程大纲/报告/PDF) → 库增量

用户丢一份外部资料说「学习里面的手法,补我们的 skill」时的流程(入口是**资料**,不是上面的报告沉淀):

1. **抽全文落盘再读**:PyMuPDF 抽 PDF/PPT 文本 → 写 `$LOCALAPPDATA/Temp/<名>.txt`(`encoding="utf-8"`,逐页插 `===== PAGE N =====` 分隔),
   再用 `read_file` 读这个 txt。**不要直读 PDF**(二进制,只回乱码),**不要把全文打到 stdout**(必被截断)。
2. **缺口比对,只补真缺口**:先列资料的主题清单,再与全库 `security/*/SKILL.md` 的 name+description 做关键词比对
   (`execute_code` 跑脚本汇总,别肉眼扫)。库里已有同族卡 ⇒ **回填**(该卡加 `references/<主题>.md` + SKILL.md 一行指针);
   确认空白 ⇒ 才建新卡。同一主题不建第二张卡。
3. **建 class-level 卡**(不是「某资料某章」卡):名=攻击面家族名,目标可横向替换;SKILL.md 薄(骨架+判据+真源清单),
   细节进 `references/<主题>.md`,可跑的探针进 `scripts/`。
4. **探针必须自证**:每个 `scripts/*.py` 支持 `--selftest`(内置 mock 服务/合成样本,离线可跑),
   **当轮实跑一次**,用真实输出(命中数/PASS)决定能不能在 SKILL.md 里写「已实测」。写不出自证路径的脚本别放进卡。
5. **交付前校验**:全库截断标记 grep(严格正则,排除扫描器自身与本卡)· 逐文件 `wc -c` 对量级 · `tail -3` 看末句完整 ·
   `find security/<名> -type f` 确认 SKILL.md 与 references/scripts **同目录**。
6. **登记镜像**:新卡走 `report_to_skill_sync.py --skill "名:分类:备注" --verify-name 名`;只改已有卡的附件 ⇒ 走 `--file` 回填分支。

## 附件索引(卡内所有 references / scripts)

| references | 什么时候读它 |
|---|---|
| `core-handbook-index.md` | 换会话/上下文被压缩/隔天续跑/被要求「重新学习我的经验」 |
| `report-decomposition.md` | 拿到报告/大纲/PDF 要落卡: 切几刀、哪张新开哪张回填 |
| `pack-absorption-workflow.md` | 收到整包技能(zip/目录)要「以现有库为基准补充完善」 |
| `skill-consolidation-playbook.md` | 库内窄技 → 家族总技聚合(合并/`absorbed_into`) |
| `organizer-classification-and-cleanup.md` | 新建/改名技能后要让 D: 镜像跟上;或发现技能「凭空消失」 |
| `session-audit-methodology.md` | 「把历史会话里没沉淀的一起整理」 |
| `library-digest-via-parallel-subagents.md` | 「学一遍我所有 skill」/冷启动建全库认知(禁止逐个 `skill_view` 灌上下文) |

| scripts | 用途 |
|---|---|
| `report_to_skill_sync.py` | 报告→卡 六步一键(新卡/回填/文档/校验) |
| `verify_skill_sync.py` | **体检器**: 7 项 卡↔镜像一致性;`--selftest` 自证 |
| `mirror_one_skill.py` | 精准镜像单卡(勿自己 `json.dump` 索引) |
| `mirror_dryrun.py` | 全库跑前干跑:看会删哪些陈旧镜像 |
| `draft_categories_for_unregistered.py` | 未登记卡**起草**分类(近邻投票+硬规则);`--apply-all` 落库 / `--fix-notes` 回写脏 note |
| `archive_stale_mirrors.py` | 退役卡(`.archive/`)的旧镜像 → `_trash_<日期>` 可逆归档 |
| `audit_digest_coverage.py` | 全库摘要覆盖率审计 |

★ 规矩: 新建附件**同时**在这里加一行(否则下个会话读不到 = 隐形资产,校验器 C4 会直接点名)。

## 15 大分类 (taxonomy, 2026-09-14)

| 目录 | 数量 | 范围 |
|------|------|------|
| 01-web渗透 | 106 | SQLi/XSS/SSRF/SSTI/XXE/GraphQL/SPA/SaaS/卡密商城/赌场/API/TG bot/TG小程序/低代码后台/AI agent运行时 |
| 02-逆向破解 | 34 | EXE/Nuitka/fndata/注册机/脱壳/Go/.NET/Python/iOS/固件/Flutter/Dart/Auto.js/docker提取/游戏内置外挂(so替换植入) |
| 03-网络渗透 | 17 | 端口/提权/横向/持久化/隧道/AD/后门/WireGuard pivot/Windows文件取证 |
| 04-云安全 | 13 | AWS/Azure/GCP/K8s/Docker/CF源站绕过/空间测绘 |
| 05-移动硬件无线 | 17 | 安卓/WiFi/NFC/RF/USB/车/无人机/ICS/SCADA/VoIP |
| 06-密码OSINT社工 | 16 | 密码破解/OSINT/钓鱼/隐写/加密货币/混币/钱包 |
| 07-恶意软件取证 | 14 | 免杀/勒索/rootkit/取证/漏洞研究 |
| 08-红队C2 | 10 | C2/Shellcode/ROP/浏览器利用/游戏破解/零信任 |
| 09-综合辅助 | 20 | 技能安装器/态势评估/回退/报告生成/作战指挥(cyber-ops)/复盘回写(ops-review)/情报摄入(intel-ingest)/COD运维/TG数据机器人/跑分 |
| 10-AI与Agent基建 | 9 | Claude Code/Codex/OpenCode 委派/多智能体/性能调优/AI生图服务 |
| 11-研发工程 | 33 | 开发调试测试TDD/代码评审/GitHub 工作流/DevOps/数据工程/MLOps |
| 12-生产力办公 | 22 | 文档表格PPT/PDF/邮件/日程/知识库/比价/法律文书 |
| 13-创作设计 | 22 | 设计稿/信息图/架构图/ASCII/动画/音乐/着色器/p5.js |
| 14-研究与情报 | 8 | 论文检索/博客RSS监控/竞品跟踪/引证/付费与WAF页绕过 |
| 15-平台与设备 | 8 | macOS应用/智能家居/社媒API/采集管道运维/元宝群组 |

## 合并(absorbed_into)操作规范

**先判来源归属,再决定能不能动。** 归属查两处:

```python
# ~/AppData/Local/hermes/profiles/123/skills/.curator_ledger.jsonl (868 行,7MB)
# 逐行 json.loads,搜技能名;action=='create' ⇒ curator 创建(可改可删)
# 只在 'write_file' 出现或无记录 ⇒ 用户安装技能(不可 patch/delete)
```

- **双方均 curator 创建** → 可合并:全文吸收(被吸收方 SKILL.md 保留在「合并吸收」小节)+ references/scripts 全部搬运 + 同名附件加 `原名__` 前缀,然后 `skill_manage(action='delete', absorbed_into=<保留者>)`
- **一方用户安装** → 只写进报告,不动作
- 合并后**必须**:
  1. 校验「丢失行 = 0」(被吸收方正文每行仍能在合并文件里找到)
  2. 全库 grep 被删技能名 → 修 `related_skills`/正文里的悬空指针(2026-09-14 修了 5 处)
  3. 重跑两个脚本(会自动清掉旧镜像)

- **只加/改几张卡时用 `mirror_one_skill.py` 逐个精准镜像**，**别跑全库** `organize_skills.py`：
  全库会把 16 个「源卡已消失」的镜像一并清掉（实测 `windows-binary-*`、`fndata-auth-bypass` 等用户装卡）。
  用 `--help` 看参数：`mirror_one_skill.py <skill-name> <NN-分类目录> ["备注"]`（拷贝+更新 JSON+重建三份文档，一步到位）。
- **只 patch 了既有卡的 references/SKILL.md 也要重跑 `mirror_one_skill.py`**，否则镜像留在旧版；
  D 盘镜像里没有该卡（未登记类）就先补进 `CATEGORIES` 再镜像。
- **校验口径**：改完后按相对路径逐个文件对 md5（源 vs 镜像）——`缺/异/多` 三列全空才算同步；
  光看「OK 索引 N 条」不够。
- **`skill_manage(action='create')` 把新卡落在 `skills/` 根目录**，不会自动进 `security/`；
  建完要 `mv <name> security/`（先 `mkdir -p security/<name>` 再搬 SKILL.md 更稳），否则镜像与索引都找不到。

## 已合并记录

| 日期 | 保留 | 被吸收 | 依据 |
|---|---|---|---|
| 2026-09 | `cloudflare-bypass` | `cloudflare-origin-bypass` + `cloudflare-origin-discovery` | CF 家族总技 |
| 2026-09-14 | `volcore-pentest` | `volcore-api-pentest` + `volcore-lowcode-pentest` | 同一套 Vol.Core 默认 secret/claims/表驱动 API |
| 2026-09-14 | `filament-admin-pentest` | `filament-livewire-admin-pentest` | 同为 Filament v3/Livewire 后台渗透 |
| 2026-09-14 | `tg-bot-operations` | `tg-bot-operations` | 同为 TG 数据推送 bot 运维 |

## 待处置重叠(阻塞在来源归属)

`windows-binary-cracking` ↔ `windows-binary-reversing` ↔ `windows-exe-cracking` ↔ `windows-exe-crack-methodology`(4 个同题,全部用户装,不可动);
`data-exfil` ↔ `exfiltration`;`credential-stuffing` ↔ `online-credential-stuffing`;`saas-webapp-pentest` ↔ `saas-multitenant-pentest`;`php-security-audit` ↔ `php-webapp-security-audit`。
详见 `技能库\_index\重叠与合并建议.md`。
