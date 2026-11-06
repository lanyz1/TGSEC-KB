# 技能库可调用性体检（invocation integrity audit）— 详细流程与实例

场景：用户问「渗透过程中还能准确调用到每一个技能配置吗／其他机器同步后技能能不能用／给技能库做体检」，或库近期发生过增删改名、脚本源变更、跨机同步。目标：证明"打起来每张卡调得到"，而不是只证明脚本能跑。

路径锚点（TGSEC 环境实例）：本机安装真身 `~/.hermes/skills/<类>/<名>/SKILL.md`；仓库技能源 `.claude/skills/<名>/SKILL.md`（仓库位于 /root/TGSEC-Qtzuu/，其他机器路径不同）。

## 四件套细节

1. **全量清点**：`find ~/.hermes/skills -name SKILL.md` 计数 + 按分类计数（2026-10-12 体检时 1203 张）。
2. **★撞名扫描（最狠的炸点）**：收集所有 SKILL.md 的父目录基名做 Counter；count>1 = 裸名调用 `skill_view(name)` 直接报 **Ambiguous 拒载**（实测铁证：`docx` 裸名拒载）。
   - 处置约定：**不动官方/裸名件**；测绘/自铸件改名加后缀（先例 `pdf`→`pdf-processing-pro`；同批 `docx`/`xlsx`→`docx-processing-pro`/`xlsx-processing-pro`）。
   - 改 **dir 名 + frontmatter `name:` 字段**两处都要改；改完实弹复测：裸名一发→官方件、新名一发→测绘件，两条都绿才算消弹。
3. **污染扫描**：技能树内不得有 `*.bak*`（解析歧义源）；同步脚本的备份要落在技能树外（如 `.hermes/skill-backups/`）。
4. **frontmatter 体检**：每张卡头 2KB 内须有 `name:` + `description:`；缺失补齐（实例：`gpu-hunter`、`undying-persist`）。
5. **名实不符**：dir 基名 ≠ frontmatter name（如 `mobile-reverse`=移动端逆向）**不用修**——英文目录名与中文显示名两个通道都能直调（双通道实测均通）。

## 伞形引用链体检（本机 + 仓库双份）

- **多基准解析**：每条 ref 依次对 [技能自身目录, 包根, 仓库 `.claude/skills/`, 本机 security 目录, 兄弟技能目录] 求解析。单一基准会产生成片假缺失（血泪：拿仓库根解析本应相对技能目录的 `techniques/*` → 成片假断链；修前必须多基准复检）。
- **假阳性排除**：`...`、`YYYY-MM-DD`、`<面>` 等占位不算；`upstream-*` 是命名约定；引用出现在"反面示例"文字里（如 "creating domains/src-hunting was rejected"）不算。
- **真断链修法（跨机可用性优先）**：
  - 共享技术库 → 文件系统相对路径 `../pentest-redteam/techniques/x.md`（skills 安装后彼此同级，换机可解析）。裸 `techniques/x.md` 依赖解析基准、外部绝对路径（如 /root/Black-cat 原装安装）换机必瞎。
  - 案例引用 → 全路径 `domains/<域>/case-lessons/<file>.md`（简写 `gambling-pentest · case-lessons/x` 不可机械解析）。
  - 跨技能 references → `../<skill>/references/x.md`。
  - 外部装机引用（如 /root/Claude-BugHunter）= 条件引用，按设计保留，**不算断链**。
- 修完：双份同步改（本机 `~/.hermes/skills/...` + 仓库 `.claude/skills/...`）→ 复扫清零 → 仓库侧 commit + guard + UPDATE 记账。

## 跨机同步语义

- 仓库技能源 = `.claude/skills/`（全跟踪）；仓库里 `hermes-skills/` 是历史瘦身剔出的死目录（被 .gitignore 忽略），旧同步脚本若认它会挂——脚本要能回退源解析（env 显式覆盖 > 默认 `.claude/skills/`；缺源跳过自拷）。
- **pull ≠ 技能更新**：其他机器 pull 完必须重跑 sync（`scripts/sync-agent-skills.sh` 等）把伞形/卡装进各 agent 目标目录才算拿到新卡。
- 推库纪律：commit → 推前 guard 扫描（clear to push）→ 用户口令 → 推后 `ls-remote`==本地 HEAD 才算数。
- 本机版与仓库版内容密度差要单列（实例：PE references 117 vs 26、SKI 9 vs 5）——是「内容增量未回灌」，**不影响调用**；回灌要用户点头。

## 压缩风暴下的作业纪律（长会话实测）

- 超长 execute_code 脚本有被截断风险（实测 SyntaxError：第 7 行字符串被腰斩）→ 脚本拆 <1KB，或改用 patch 工具逐文件小刀。
- 关键结果落盘（/tmp/xxx.txt）后 `read_file` 读回核验——输出被吞时这是唯一可靠通道；git 状态可 `read_file` `.git/COMMIT_EDITMSG` 核验。
- 修复脚本写成**幂等**（先检查再应用 + 计数断言），看不到上次输出也能安全重跑。
- 单行小输出比大输出存活率高；提交后核验用 `rev-parse --short HEAD` + `status --short` 两行钉死。

## 实例档案（2026-10-12，TGSEC）

- 1203 技能全量体检：炸点 2 类（`docx`/`xlsx` 撞名实测 Ambiguous；2 缺 frontmatter）+ 伞形真断链全修（black-cat techniques 7 行 + 使用方式、PE 案例 2 条、CDN 1、SKI 1）→ 全修全测；提交 `b401bbe1`。
- **闭环（已推）**：5 提交 `047b0a83..b401bbe1` 推上远端（39 文件）；推前双器绿（全史 33,287 对象 / 25,289 blob、16 硬族 ZERO、soft 83；verify_final hard=0）；推后三件齐平验收（三方针 == `b401bbe1`、反向克隆 82 提交对齐、404 探针 `c570571c/df5bd0aa/220a58f4/f5a28386` 全 "Not a valid object name"）。细则与日志惯例见 security-kb-ingest `references/push-guard-acceptance.md`。
- 已修：`black-cat-redteam` 双份（仓库+本机）7 处 `techniques/*`→`../pentest-redteam/techniques/*` + 使用方式相对化；`UPDATE-2026-10-12.md` 追加 fix 记账节。
