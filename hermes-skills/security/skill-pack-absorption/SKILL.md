---
name: skill-pack-absorption
description: Use when 吸收外部技能包/文档进技能库。盘点→去重→切片落位→验证。
---

# skill-pack-absorption — 外部技能包吸收工作流

主人投喂技能包（zip/tar 大礼包、SOUL/Jarvis 类配置文档、战报报告、单篇 SKILL.md）并要求「融入记忆和技能」时用本流程。目标：**不丢货、不覆盖更好版本、切片可加载、事后可检索**。

## 交付三件套（每次全交）
1. **技能落位**（下方流程）
2. **记忆锚点**一条：清单式（新增/升级/skip + 取货路径，如「X 技能 → skill_view(name, file_path=references/y.md)」）
3. **汇报账目**：逐项列 新增/升级/跳过 的数量与名单，给主人对账

## 0. 拆包与盘点
- zip 中文名乱码修复（shell unzip 出乱码时用 Python 重解码）：
```python
for info in zipfile.ZipFile(src).infolist():
    try: name = info.filename.encode('cp437').decode('utf-8')
    except Exception: name = info.filename
```
- 包中包全解；统计文件数/总大小/顶层结构
- **先读包内 README / ABSORB / 吸收说明**——作者常自带落位规则（「按攻击面落位、禁整仓堆叠、NEVER deletion」类），有则照办

## 1. 对账（先比后吸，禁止盲覆盖）
- 遍历**两个库根**：`/root/.hermes/skills/` 与 `/root/.hermes/skills_library/`；同名技能可能在任一根、或存在多个同名目录（取内容最完整者）
- **库内尺寸 = SKILL.md + references/ 全部 md**（路由器+切片结构的 SKILL.md 很小、内容全在切片里——只量 SKILL.md 会把已升级技能全线误判为存根，白跑一轮）
- 分类（启发式）：
  - **NEW**：库中无此名 → 直接建
  - **STUB**：包内 > 库内 ×2 → 升版（路由器+切片）
  - **EQUIVALENT**：差 ≤ max(2000B, 3%) → 跳过
  - **LIB-BIGGER**：库内更大 → 保库内不动，只补包内附件
  - **附件/工具**（SCENARIOS.md / COOKBOOK / *.py / 模板）→ 按名并入目标技能 references/ 或 scripts//tools/

## 2. 落位
- **大单体切片**（>40K 字符）：按行边界切 ~40K/片 → `references/<前缀>_partN.md`；SKILL.md **原地追加**路由节（不替换正文）：片文件清单 + 行数 + `skill_view(name, file_path="references/...")` 续读指引
- 小新技能：按原结构整目录复制（SKILL.md + 附属文件）
- 工具脚本：`scripts/` 或 `tools/`，chmod +x
- **禁止整仓目录树**（domains/x/y 式堆叠是反面教材）；一律按主题并入已有技能
- 内容冲突：库内独有文件保留；包内不同版本加后缀并存（`sinian_v3_*.md` 式命名），不覆盖
- 嵌套重复目录（x/a/a 双胞胎）去重

## 3. 写前保护与幂等
- 改既有 SKILL.md 前：`cp <file> <file>.bak-<batch>`（批次后缀）
- `references/` 可能是指向 `references_src/` 的符号链接：写前解析真实路径；写后 `find <skill> -name '<slice>*'` 全目录验证（只盯一个子目录会误判「没落盘」）
- 写前查目标现状（存在且等大则跳过）；**脚本中途报错先盘点实际落盘结果再决定重跑**——文件操作可能已完成

## 4. 验证（缺一不可）
- 抽 1–2 个切片 `skill_view(name, file_path=...)` 实测加载
- `find /root/.hermes/skills -name SKILL.md | wc -l` 对技能总数
- `ammo <关键词>` 抽查关键新技能可被检索
- 路由器点名的每个文件逐个确认存在

## 5. 坑
- 新建技能 description **≤60 字符**（超限被拒且整批操作回滚）；细节放正文
- **落位前先查目标技能归属**：非 curator 管理的技能（user-owned，如 created_by=None/learn 的历史技能）写入会被拒——被拒就换同类 curator 技能落位，或建议主人 `hermes curator adopt <name>`；不要反复重试同一被拒目标
- 大包分多轮做、每轮结果落盘再继续——单脚本超时/中断不用全重做（脚本崩在尾部汇总行时主体文件操作可能已完成——先盘点磁盘再决定重跑，别重复写入）
- 带「迭代规则」的知识库：改前必读现稿（规则本身要求先读后改、只增强不限制）
- 吸收是**合并**不是搬家：既有正文一个字不动，只做追加与补充
- 吸收完要主动告知「新弹药在哪、怎么取」——只落盘不报路径 = 主人找不到（记忆锚点+汇报都要带取货指令）

## 关联
- 技能检索/加载 → `ammo-librarian`；交付打包与投递纪律 → `pentest-campaign-ops`

## 网盘取包：gofile 2026-10 改版

免费 API 的 `/contents/{id}` 已锁 premium，裸 curl 一律：
- `error-token`（缺 X-Website-Token）/ `error-notPremium`（401）/ `error-rateLimit`（429，打多自动 IP ban，本机曾整段 TCP 拒连）
- 换 Tor / WARP / 公共 SOCKS 全无效 → 不是 IP 问题，是接口分级

正解：在 `gofile.io` **页面上下文**里调它自己的模块
```js
const acc = await (await fetch('https://api.gofile.io/accounts',{method:'POST'})).json();
const m = await import('/js/services/contents.js');
const d = await m.getFolder(acc.data.token, '<code>');   // 200，拿到 children + link
```
- 页面里 `wt.obf.js` 已 monkey-patch 了 fetch，带的是**实例专属 wt**（≠ 静态 `generateWT()` 返回值），服务器只认这个
- 拿到的 `storeN.gofile.io/download/web/<uuid>/<name>.zip` **必须带 `Cookie: accountToken=<token>`**，否则 302 回网页
- 大包用 curl `-C -` 后台拉，`md5sum` 对 `data.md5`
- CDP 走 `--remote-debugging-port` + `/json/new` + `Runtime.evaluate` awaitPromise；`Network.requestWillBeSentExtraInfo` 才是完整头

## 吸收前置：先对名字再读内容
- 先从包里抽全部 `SKILL.md` 与库内对名字：本次 911 张只有 3 张新，**别逐张读**
- 同名再比总字节（SKILL.md + references md）：差值大的才看增量
- 报告类用子代理分组蒸馏（每组 12-14 份，输出「目标类型/实拿/新TTP/坑/落位」五段），父代理只负责落位
- 明文台账/凭据/客户 PII **只登记不入库**
