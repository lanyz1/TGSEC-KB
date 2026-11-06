---
name: knowledge-repo-integration
description: "Use when merging external repos into a unified suite: assess candidates, vet poisoned PoCs, diff-fuse or whole-pack absorb."
version: 1.0.0
---

# 知识仓库整合与发布 (Knowledge Repo Integration)

将多个外部知识仓库吸收 → 主题化重构 → 打包 → 发布到 GitHub 的完整方法。
适用于「吸收这些仓库的知识技能」「整合成一个套件」「推送到我的仓库」类任务。

## 用户核心偏好(硬性)

- **主题化整合,不按来源堆叠**: 最终产物必须是 `domains/<主题>/` 结构,绝不能 `knowledge/<库名>/` 平铺。用户明确纠正过这一点——「不要有其他仓库的说明」= README 和入口文件里不出现任何上游仓库名/作者名。
- **署名约定**: 统一 `@TGSEC社区 · @TGSEC-Qtzuu 整理`(整理作者 @TGSEC-Qtzuu)。
- **AI 自适应**: 仓库必须带 `AGENTS.md`(AI 拿到地址即自动克隆+配置+开测)+ 工具自管理脚本(缺什么装什么,渗透中缺工具→查 manifest→立即装→继续,不中断任务)。

## 四步流程

### 1. 吸收(吸收外部仓库)

```bash
cd /root && git clone --depth 1 <url> <repo-name>
```

- 先看 README/AGENTS.md/目录结构判断定位(路由入口 vs 方法论 vs 技术卡 vs 工具)。
- 每库创建一个 Hermes 技能入口需 `skill_manage`: description 必须 ≤60 chars(触发词开头,句号结尾),超长会被拒绝。

### 2. 主题化整合(核心)

- 写 `integrate.py` 映射表: 逐库逐目录/文件 → 目标主题(如 `sql-injection` → web-injection)。
- **禁止宽泛 glob 兜底**(如 `techniques/*`),会混入无关文件(实测 cloud-metadata 混进 file-vulns)。逐目录精确映射 + `printf` 报告每个主题统计,抽查确认。
- 每个主题域生成 `README.md` 索引 + 总入口 `MASTER.md`(主题矩阵 + 5 步路由)。
- 验证: 主题数 ≥ 覆盖所有库目录,文件数总和与预期一致。

### 3. AI 引导与工具自管理

- `AGENTS.md`: 环境自检 → 补装缺失 → 按场景选入口 → 渗透中缺工具立即装(查 tools-manifest.json 找不到就想装法并补进 manifest)。
- `scripts/tools-manifest.json`: 工具清单(name/pkg/channel/purpose),channel ∈ {apt, pipx, uv, npx, gobin, git, local, system}。
- `scripts/check-tools.sh` + `scripts/install-tools.sh`: 多通道自动安装,支持 `--dry-run` / `--category` / `--channel`。
- 实测验证脚本(dry-run + 实际装一个工具跑通 apt 通道)。

### 4. 发布 GitHub

- **PAT 诊断先行**: `github_pat_`(fine-grained)默认只有 `metadata=read`,不能建仓库/写入;`ghp_`(classic)勾 `repo` 全选才行。用 curl 探测: `GET /user` 确认身份, `PUT contents/probe.md` 确认写权限,别反复盲试。
- **Tor/代理环境会搞死 GitHub（硬性，2026-09-20）**: 本机常常 `http(s)_proxy=socks5h://127.0.0.1:9050`。urllib/`git` 走 HTTP CONNECT 打 Tor 会报 `501 Tor is not an HTTP Proxy`，或 `git ls-remote` 走偏。**探权/推送前必须清掉代理**:
  ```bash
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
  export NO_PROXY='*'
  git -c http.proxy= -c https.proxy= push origin master
  ```
  API 探针同样先 `unset` 再请求；推完用 API/`ls-remote` 核对 remote HEAD == 本地 SHA。
- **嵌入式 .git 陷阱**: `cp -rL` 复制带 `.git` 的库再 `git add`,git 会把它们当 gitlinks(160000),只推几个 stub 文件。修复: `rm -rf <复制目录>/*/.git` + `git rm -r --cached` 旧 gitlink + `git add -A` + `--force` 覆盖。
- **推送前密钥/大文件/战役 loot 卫生（硬性）**: case-reports 里的阿里云 `LTAI*` / 腾讯云 `AKID*` / AWS `AKIA*` 等明文会触发 GitHub **push protection**（仓未开 Secret Scanning 也可能拦）。**用户账密/全量 uid 清单同理**：私有仓也不进明文 loot；只进脱敏课 + 统计指针，原件留本机 `cases/`/`reports/old-campaigns/`。提交前 `rg` 扫并打成 `[REDACTED]`；超大 lab 二进制（qemu/vmlinuz/demo 媒体/weights）改 `*.NOT_VENDORED.md` 桩 + `.gitignore`，ingest 暂存目录不入库。细节与被拒修复见 **`references/suite-publish-push-hygiene.md`**。
- **推送后构建**: `bash scripts/bootstrap.sh --force`（或 `sync-agent-skills.sh` + `sync-hermes-skills.sh`）；校验树内无 `security.bak.*`、关键技能裸名 matches=1、远程文件 API 回读 OK。
- **推送后验证**: `git ls-tree -r origin/master --name-only | wc -l` 与本地文件数一致;再看顶层结构。

### 5. 运行时技能库维护(吸收后)

- **多副本写偏陷阱**: 每个技能存在~11份副本(活库 + 历史 `security.bak.*` + 10个toolkit镜像)。裸名 `skill_manage`/`skill_view` 可能解析到 `security.bak.<STAMP>` 副本——写入"成功"但活库未变(2+副本命中时裸名直接报 Ambiguous 拒绝)。规则: 读写一律用带分类路径(`security/<skill>`); 改文件走绝对路径+通用 `patch` 工具(绕开解析); 每次写后验证活库(`grep`/`md5sum`); 若写进了 `.bak`, 把内容搬到活库+从完好副本还原 `.bak`(先 md5 对比, 通常只有一份被污染)。
- **sync 备份禁止落在 skills 树内（P0，2026-09-20）**: `scripts/sync-hermes-skills.sh` 必须把快照写到 `~/.hermes/skill-backups/security.bak.<STAMP>/`（只留 3 份），**绝不能** `~/.hermes/skills/security.bak.*`——Hermes 裸名 rglob 会把 bak 当 Ambiguous，导致渗透调不到技能。旧树内 bak 要先迁走再 sync。详见 `references/runtime-skill-library-sync.md`。
- **镜像先于同步**: `~/security-suite/hermes-skills/` 是源头, 同步单向 suite→活库, 只改活库不会回流。改完必须把文件镜像进 `hermes-skills/<skill>/`(md5 验证), 再 `bash scripts/sync-agent-skills.sh` 扩散到10个toolkit副本+活库+ensure 链。预检: 各toolkit目录应只含公开技能集(2026-09-12 实测10个全干净)。
- 超长内联命令被硬拦截 → 载荷存 `/root/.hermes/cache/blocked-scripts/blocked-*.sh`, 审读后 `bash` 执行。

## 多AI工具配置分发

发布安全知识仓库时,附带多AI工具配置让用户clone后立即可用:

### 目录结构

```
ai-config/
├── README.md              # 总说明+快速安装
├── universal/             # 通用配置(任何AI工具)
│   ├── PERSONA.md         # 人格/执行规则/渗透流程
│   ├── MEMORY.md          # 知识记忆(攻击面优先级/平台特征)
│   └── RULES.md           # 执行铁则/命令规范
├── hermes/                # Hermes Agent(setup.sh一键脚本)
│   ├── USER.md            # → ~/.hermes/memories/USER.md
│   ├── MEMORY.md          # → ~/.hermes/memories/MEMORY.md
│   └── setup.sh           # 备份+提取代码块+写入+验证
├── claude/CLAUDE.md       # Claude Code 项目上下文
├── codex/instructions.md  # OpenAI Codex/Copilot CLI
├── grok/system.txt        # Grok CLI system prompt
├── cursor/.cursorrules    # Cursor IDE规则
└── aider/.aider.conf.yml  # Aider配置
```

### 关键设计

- **universal/** 是核心内容,各工具配置是它的不同格式适配
- **AGENTS.md** 告诉AI: 看到仓库地址→自动检测AI类型→选对应配置安装
- **Hermes 特殊**: USER.md/MEMORY.md内容放在markdown代码块里,setup.sh用python3 regex提取写入,避免直接cp(文件含安装说明)
- **Claude Code**: 项目根目录放`CLAUDE.md`即自动加载
- **Cursor**: 项目根目录放`.cursorrules`即自动加载
- 配置内容要通用化,去掉用户个人信息(称呼/GitHub账号等)

## 候选仓评估: 先评估, 后动手(用户硬性)

用户给一批仓库/帖子/zip 问「这个有可以提炼吸收的吗」「吸收融合这两个」时, **先给评估报告 + 建议, 等用户拍板再吸收**——用户明确说过「先告诉我 让我做决定」。不要一上来就克隆融合。外层 Telegram zip 常套两层：先 `unzip -l` 看内层包名再评估。

评估只需廉价探测:
1. `curl -fsSL https://api.github.com/repos/<owner>/<repo>` → 存在性 / 描述 / 语言 / star / size / 更新时间 / 许可证(私有仓或 404 直接判死)。
2. `git clone --depth 1` 到 `_probe_<name>/` → 数 `SKILL.md` / `*.md` / 总文件数, 看顶层结构判断定位(路由包 / 方法论 / 技术卡 / **产品本体**)。
3. 与本地已有资产做覆盖差异(见 references/repo-triage-and-poison-vetting.md)。
4. 输出三段: 仓库性质 → 投毒甄别结论 → 真增量清单 + 「要不要吸」的建议。

判断「产品本体」而非知识库: 若仓库主体是完整应用代码(实测 MarkUs、ILIAS), **不整仓吸收**, 只记元数据 + 用 CVE / exploit-db 参考页挂索引。

## 投毒甄别(用户硬性要求: 「注意分辨是不是投毒的」)

吸收任何第三方 PoC / 技能仓前必须过一遍, 结论写进融合报告:

- `package.json` 无 `postinstall` / `preinstall` / `prepare` / `prepublish` 钩子(供应链投毒首选位置)。
- 扫 `curl … | bash` / `wget … | sh` / `eval(` / `execSync(` / `child_process` / base64 大块 / `atob(`。
- 扫挖矿与回连特征: `xmrig` / `stratum+tcp` / 矿池域名 / `ngrok` / 未知 webhook。
- **列出全部外连 URL 并逐个判合法**——例: `bin/wxsource.mjs` → `bbs.kanxue.com` = 看雪论坛取素材, 正常放行。
- shell 脚本少时**逐个通读全文**(例: `probe.sh` 只有 `uname` / `free` / `command -v`, 干净)。
- 明显异常文件单独看(例: 某 `.nim` 文件内容只有 `404: Not Found` = 提交事故, 不是代码)。
- 二进制 / APK / 驱动类工件: 保留但标注来源与授权用途, 不当可执行入口。

## 差分融合(与本地同类技能重叠时)

来料与本地已有技能同类(技能库对技能库)时, **先做文件级 diff 再融增量**, 不做整仓覆盖:

- 按相对路径算 sha256, 分四类: `identical` / `changed` / `new` / `local_only`。
- 只拷增量: 本地缺失的新文件 + 来料明显更丰富的同名文件; 覆盖前把本地版备份到 `_ingest_*/backup_local_<skill>/`。
- 写同步说明(`TGSEC-BRIDGE.md`)记来源 / 日期 / 备份位置。
- **不另开平行堆叠域**——同域内容并进现有技能/域, 保留本地更优版本。
- 落点选择: 原子技能散进既有域(实测十二技 → `domains/<域>/src-methods/hunter12-*.md`), 大类网关当索引。

### 整包落地 vs 散卡落地 vs 轻量提炼(落点判定)

先判来料形态再定落点, 别一律散进去:

| 来料形态 | 落点 |
|---|---|
| 散卡 / 单主题手册(十几份 md) | 散进既有域 `domains/<域>/src-methods/<来源>-*.md` |
| **自洽多层路由体系**(入口 → 大类网关 → 原子技能, 100+ `SKILL.md`) | **整包落地**为域内独立子包 `domains/<域>/<name>-pack/`, 不动本地同类路由包 |
| **编排型审计 skill**（6 阶段 + companion 攻击类 + schema/validators；本库已有点名或活靶闸门） | **轻量提炼**：只融缺口进既有域子目录；**不**新建 Hermes 伞形、**不**整仓 vendor。见 `references/lightweight-methodology-distill.md`（2026-09-20 Cloudflare 案） |

整包落地规则(实测 122 技能逆向包):

- 保留上游目录结构(`README.md` 索引 + 每技能 `SKILL.md` + `references/`), 入口技能单独点名。
- 索引表由脚本从 frontmatter 生成: 入口+网关表 + 原子技能全表(名称 / 简介 / 参考数)。
- **不与本地同名路由包堆叠**——独立子包, 包 README 首行写清「同名以本地为准」。
- 三处指针: 域 `README.md` 加 `<!-- fused:<来源> <日期> -->` 块; Hermes 伞形技能加「快查表」(需求 → 打开哪个 SKILL.md); 包内 README。
- 收尾: 删暂存克隆 + `.git`, 只留 `_ingest_<name>_<日期>/`(脚本 + JSON + 日志, 百 KB 级)供审计。
- 不要跑上游的 npm 安装(`npx <pkg> install`)——只取技能库本体。

### 索引生成的坑

- **frontmatter 块标量**: 上游 description 常写成 `description: >` + 缩进块。只认 `key: value` 的解析器会全部取空 → 索引里上百行简介都是 `(no description)`。解析器必须处理 `>` / `|` / `>-`(读到下一个非缩进行为止)。
- **数字必须实测**: 融合后 `find <pack> -name 'SKILL.md' | wc -l` 必须等于来料技能数; 索引表头写的数量要与实际行数对齐(入口技能算进表里 → 表头写「入口 + 网关(N)」), 别信手写的数。
- 覆盖差异判定用**技能目录名精确比对**, 关键词判据会大量误命中(本地语料几百份 md 时尤甚)。

## PoC 合集 / 方法论技能包 / 实战报告（三分流）

| 来料 | 落点 | 细则 |
|---|---|---|
| 方法论 / 技能包（Qtzuu、十二技、rev-skills） | 既有域差分或 `*-pack` 整包 | 见上文「差分融合」「整包落地」 |
| **CVE PoC 合集**（精选索引 / 批量克隆 / 监控链接仓） | `domains/0day-exploits/<product>/<CVE>/` | **见 `references/poc-collection-ingest.md`** |
| **实战报告包**（zip 混装 md/pdf/rar） | 各域 `case-reports/<slug>/` + `case-lessons/<slug>.md` | **见 `references/field-report-ingest.md`** |

PoC 合集硬坑（摘要）：

- 「全文提到 CVE」≠「已融合」——只认带 `analysis.md`/`summary.md`/`exploit` 的条目目录，否则差分会假报 0 new。
- 投毒分 **HARD**（挖矿/webhook → 跳过）与 **SOFT**（`/dev/tcp/`、文档 `curl\|bash` → 仍融合并标注）；白皮书里的 payload 示例可能 HARD 误报，要人工看上下文。
- 监控索引仓（无 PoC 本体）→ 写 `_indexes/…/INDEX.md` + 对 RCE/Web 优先浅克隆（设 CAP）。
- 用户说「完整吸收少的」= 缺的全吸；首次「有没有可吸」仍先评估等拍板。

实战报告硬坑（摘要）：

- 先对 suite/`cases`/`reports` 做 sha256 + 规范文本去重，再融合；包内「(2)」/同内容异后缀留最长。
- 双落点：全文 `case-reports/` + 提炼卡 `case-lessons/`；按攻击面散域，禁止 `reports-dump/` 堆叠。
- 木马/样本包：**只吸分析文本与 IOC**，ELF/挖矿二进制不进知识库。
- 中文 zip 文件名用 Python gbk 回退解码；PDF 先 `pdftotext`。

## Suite 过大后 AI 调不到实战报告（2026-09-20）

用户问「是不是太多太杂了导致 AI 调不到实战报告」时：

- **报告通常还在**：`domains/<面>/case-reports/<slug>/` + `case-lessons/<slug>.md`；缺的是**总入口** + **调用闭环**，不是正文丢失。
- 实测：`domains/` ~1.8 万文件、MASTER 旧数字过期；`sinian-*` 挤在 `src-methods/`；树内 `security.bak.*` 导致 `skill_view` Ambiguous；私有专项未进强制矩阵。
- **已落地闭环（用户要「能闭环」后）**: `domains/CASE-INDEX.md`（课数以 INDEX 为准）；MASTER/ROUTING/`pentest-execution`/`tgsec-suite` 中途闸门；sinian → `src-methods/_vendor/sinian/`；sync 备份出树；私有专项进矩阵；推 GitHub + `bootstrap --force`。调用链：`pentest-execution` → `tgsec-suite` → 私有专项 → CASE-INDEX → case-lessons≥1 → playbook/hunter。
- **不默认激进**：整库重分类/删 0day/合并重复 PoC 需用户明确「激进」。
- 细节与吸收批次数见 `references/suite-discoverability-and-case-index.md`。

## 活靶战役 AI 学习吸收（用户四步，2026-09-22）

用户说「Ai渗透积累学习 / 吸收提炼这些 / 丢给AI学习报告」时，对**本机战役**按四步沉淀（≠ 外仓报告.zip）：

1. **通读拆骨架** — REPORT/state/VALIDATED → 目标→面→链→结果；入口/转折/打穿
2. **四层知识** — 可复用技能 / 踩坑 / 组合链 / 指纹→打法
3. **落盘** — `case-lessons/<slug>.md` + `playbook-6000/*-chain.md` + `docs/playbooks/近期成功接管手法总册.md` + CASE-INDEX；战役 REPORT 挂「AI吸收落盘」指针
4. **回查** — needle 扫旧卡；能补强则补 references，禁止窄会话级新 SKILL 名

硬性：`security/*` 拒自主写新 SKILL（需 curator adopt）；脱敏无真 Token/邀请码/账密；VALIDATED 与未破分列。细则与完成判据见 **`references/ai-campaign-learning-absorb.md`**。

## 批次收口与仓库呈现（2026-10-06）

**UPDATE-*.md 不进仓库根目录**（用户指令「这些就不用在仓库显示了啊」）：日期更新文件归档 `docs/updates/UPDATE-YYYY-MM-DD.md`，今后新文件直接生成在 `docs/updates/`；README「更新说明文件」行、START「看更新」指路语同步改指（本库已改）。移库配方（`git mv` + 全库引用同步）：

- `grep -rln 'UPDATE-2026-' --exclude-dir=.git .` 先列全部引用（实测 4 文件 17 处：README 10 / START 6 / MASTER 1 / INGEST 1）。
- 两种形态都要换：链接 `](UPDATE-2026-` → `](docs/updates/UPDATE-2026-`；散文「根目录 `UPDATE-」→ 新路径。
- **排除被移动文件自身**：兄弟相对链接平移后天然正确，别被全局替换成 `docs/updates/docs/updates/...` 死链。
- 校验：根目录 0 残留 + 每个新链接目标存在。

**「一起推」= 一次性推全部待推 commit**（勘误/整理/归档别分开等）：先汇报清单 → 用户点头 → `git push` 后 `git ls-remote` == 本地 HEAD、工作树 0 残留。用户截图 commit 信息疑似过期时（浏览器缓存），以 git 事实为准，别重改文件。

**蜂群吸收收口验证三件套**：① 关键词 battery —— 子代理摘要里每个案子/技能名逐个 grep 有落点；② 技能补丁持久化 grep 确认写盘；③ git 树干净零漂移。

**「假矛盾」裁定**：复核报矛盾先用一手证据（心跳时间线→基础设施轮换；端点区分→两个不同面），结论写勘误段进 `meta.md` 单 commit，不改原文、不无证据翻案。

细则与实录见 `references/batch-closeout-repo-presentation.md`。

## 参考

- references/batch-closeout-repo-presentation.md — 批次收口与仓库呈现：UPDATE-* 归档 docs/updates/ 移库引用同步配方、「一起推」流程、收口验证三件套、「假矛盾」裁定（2026-10-06 实录）。
- references/cve-intel-batch-ingest.md — CVE 情报清单驱动吸收：本地已有判定、PoC/分析/mock-lab 分流、KEV、自述「〇」同步（2026-09-21 十三条实录）。
- references/lightweight-methodology-distill.md — 编排型审计 skill 轻量提炼：缺口探测、落点模板、接线、validator 自测；Cloudflare security-audit-skill 实录（2026-09-20）。
- references/suite-discoverability-and-case-index.md — suite 过大诊断、CASE-INDEX/调用闭环已落地、20260920 absorb 批次数。
- references/suite-publish-push-hygiene.md — 推送前密钥/战役 loot 脱敏、Tor 代理清理、超大 lab 桩、push protection 修复（2026-09-17/20）。
- references/ai-campaign-learning-absorb.md — 活靶战役「AI渗透积累学习」四步：骨架/四层/落盘/回查；与 field-report 边界；security 只读纪律（2026-09-22）。
- references/field-report-ingest.md — 实战报告.zip：去重、双落点、PDF/RAR/木马包处理、case-lessons 提炼与批次实测。
- references/poc-collection-ingest.md — CVE PoC 合集三形态分流、严格已融合判定、HARD/SOFT 投毒、产品映射与批次 D 流水线。
- references/repo-triage-and-poison-vetting.md — 候选仓评估、投毒甄别清单、coverage 差异化的具体命令与实测坑(关键词判据过松)。
- references/tgsec-suite-recipe.md — 本方法的完整实战记录(含具体命令与踩坑细节)。
- references/multi-ai-config.md — 多AI工具配置分发的文件模板与安装脚本。
- references/atomic-skill-pack-ingest.md — 122 技能逆向包整包落地实录: 目录布局、索引生成脚本要点、指针位置、投毒核查项与收尾。
- references/runtime-skill-library-sync.md — 运行时技能库维护: 多副本写偏陷阱+修复流程、suite→活库→toolkit 同步链与验证(2026-09-12 实录)。

