---
name: report-pack-distillation
description: Use when 把战报/审计报告包蒸馏成手法卡并落库验证。解包去重→抽漏洞小节→按根因落卡→口语检索闭环→台账。
---

# 报告包蒸馏：战报/审计报告 → 手法卡

主人丢来一个报告包（zip/tar，内含几十上百份渗透报告），说「吸收蒸馏里面的，主要是攻击手法，补强知识库」时用。目标：**不丢手法、不开窄卡、落完当场能搜到**。

与 `skill-pack-absorption` 的分工：那张管**技能包**（包内已是 SKILL.md），本卡管**报告包**（包内是人写的战报，需要蒸馏成卡）。

## 交付四件套

1. 新卡 + 老卡补强的落盘清单
2. `triggers.json` 口语词补充 + `arsenal_build.py` 重建后的索引数字
3. 口语检索实测（N/N TOP1）与钩子注入实测（块大小）
4. 台账 `CARDS.md`（新增/补强/未吸三段，未吸必须给理由）

## 1. 解包与去重（先做，不然白读一半）

- zip 名优先看 `entry.flag_bits & 0x800`（UTF-8），否则 cp437→gbk→gb18030 重解码
- 嵌套 zip/tar 递归解；`tarfile` 报 `TarFile is closed` 就直接 `tar xzf <pkg> -C <dest>`
- **按全文 sha1 去重**（不是前 2000 字：同模板不同目标的报告会被误判成重复，实测前 N 字哈希 219 篇→125 篇、全文哈希 219 篇→127 篇）：报告包常见 GBK 坏名双胞胎目录（`缃戠珯鎶ュ憡` = `网站报告`），不去重会把 219 篇当 219 份
- 只算 `.md/.txt` 且 ≥300 字符；`scripts/coverage_audit.py` 直接跑出「独立文档数 / 分组篇数 / finding 标题行 / 未映射清单」
- 解完先数：文件数 / 文本数 / 独立文档数 / 漏洞小节数，四个数写进台账

## 2. 抽小节，不整包入上下文

```python
pat = re.compile(r"(?m)^#{2,4}.*(漏洞|未授权|越权|注入|上传|绕过|泄露|提权|接管|伪造|重放|竞态|任意).*$")
# 每个匹配点向后切 ~1400 字符 → JSON；聚类关键词：回调签名/钱包资金/日志凭据/S3-COS/JDBC/模板渲染/云控养号
```

- 先读**最短的高信号文档**头部：报告摘要第一段就写清「什么洞、怎么打、拿到什么」
- 大报告再补细节；一次批量 4 篇 × 1.2–1.5K 字，按主题取样，不逐篇通读
- 压缩过的报告里代码块可能已被剥离（`blocks 0`）→ 从叙述句里提参数名与请求形态

## 2.5 完整性口径（被问「已经完整吸收了吗」时唯一能站住的答法）

**只报「建了 N 张卡」= 没回答。** 2026-11 的 `报告.zip`：第一轮 10 张卡就汇报，主人一句「已经完整吸收了吗」直接击穿——127 篇独立文档只映射了不到三成技术族。

三层口径按顺序给：
1. **技术族覆盖 N/N**：把 finding 标题行聚类成 ~29 族（回调签名 / 多租户越权 / 未授权接口 / 令牌会话 / 注入 / 文件 / 信息泄露 / 资金面 / 云存储 / 提权后门 / 客户端 / 业务逻辑），逐族点名「哪张卡或哪处补节」，缺的当场补
2. **逐篇处置表**（按包内目录分组）：`46份网站渗透报告 44 篇 → 技术点全映射，2 篇纯凭据不入卡` 这种一行一组；台账写进 `CARDS.md`
3. **明确不做的事**：几千条 finding 不逐条建卡，按根因归族才可复用——这句要主动说，否则会被当成漏

不入卡清单**必须列文件名 + 理由**（纯 PII/凭据、runbook/流程、ROUND/STATUS 流水、与既有卡完全重叠）——这是被追问时唯一能自证的部分。

### 第二轮补漏的固定动作
第一轮落卡后，用标题行聚类找出**没有卡承接的族**，本轮实测漏掉且值得补的高频族：
- 登录 `scene/terminal/loginType` 分支 → 免密换 token；未认证接口发**固定 token**；免密登录 URL **可重复兑换**
- 免鉴权发短信 + `validatecode` 无限试 + `resetpwd` 三步链；忘记密码的 **OTP 收件邮箱由请求体指定**
- 掩码 token（`eyJhbG...XXXX`）原样回传仍认证；前端 `window.goEncrypt/goDecrypt` 当加密 oracle（不逆 WASM）
- FastAdmin `filter`/`op` 运算符未白名单 → 跨租户；LskyPro 注册 `is_admin=1`
- 技能系统 JS 沙箱逃逸（vm2/node:vm）；公网 geth `debug` 命名空间；SMB 签名 not required

## 3. 落卡粒度（决定库形）

- **一个可复用根因 = 一张卡**：回调弱类型、JDBC 假服务端、Cognito 匿名池、日志泄凭据、内部钱包未授权、KVM 越界读
- **同族增量补老卡**：新版本区间、单站变体、一个 ACL 绕过技巧 → 追加到既有卡尾部 + 一行 `见 <新卡>` 指针；**不开一站点一卡**
- 新卡 description 前 57 字自带触发条件，正文写「指纹 → 手法步骤 → 判据 L1/L2/L3 → 坑 → 相关卡」
- 版本号、CVSS、修复版本必须回原文核对：本批初稿两处写错区间，按文章原句改回

## 4. 凭据与 PII 纪律

- AK/SK、助记词、卡密、手机号、后台口令**不进卡**；只留「字段名 + 命中位置 + 校验结论」
- 凭据处置顺序写进卡（只读验证 → 列权限 → 横向 → 找根因），但不写任何真实值

## 5. 检索闭环（不做等于没落）

```bash
cd /root/.hermes/arsenal && timeout 500 python3 arsenal_build.py   # 看 total / published bytes
python3 skill_find.py "独角数卡 回调改sign 白嫖卡密" --fast --top 1   # 每条新卡口语验证，必须 TOP1
```

- `triggers.json` 是**口语补充词表**（key=卡名），正文仍由 build 从 SKILL.md 抽；分数被旧卡（尤其 legacy catalog）抢走时**补词重建**，不改 description 硬凑
- 自动召回钩子是 keyword-only：`on_pre_llm_call(user_message=q)` → `{"context": "<skill-recall ...>"}`；传位置参数报 `takes 0 positional arguments`，`.split()` 报 dict 无 split
- 查卡大小用 `os.path.getsize(path)`（`arsenal.db` 无 `body` 列）

## 6. 台账 CARDS.md

```markdown
## 新增（N 张）| 卡 | 核心手法 | 来源文档 |
## 补强（M 张）| `老卡` ← 一句话 |
## 未吸收（附理由）| 纯 PII/凭据文件：数据不属手法；流水日志：已被 X 卡覆盖 |
## 实测| 索引 a→b；N/N TOP1；钩子注入 x–y KB |
```

## 坑

- 报告里「某站 root」「某库 45 张表」属战果不属手法，不落卡；只落可迁移的根因与判据
- 同一包内既有完整报告又有 `STATE.md/ROUNDn` 流水 → 流水只用来交叉核对时间线，不单独落卡
- 打包/凭据文件（`CREDS_LIVE.txt`、`*_creds*`、OCR 出的 PII）**只登记不入库**
- 落卡后不重建索引 = 搜不到，会被当成「没吸收」；每加一批卡都要重跑 build 并口语复测
- 补节用**批量 append 脚本 + 首行 marker 去重**（`if marker in s: skip`），一次 10–16 张，脚本失败可重跑不会写重复段
- 每轮结束核对「索引 total / enabled / triggers 条数」三个数字，汇报别只给 "已重建"

## 关联

- 配套覆盖审计脚本：`scripts/coverage_audit.py`（去重 + 标题行聚类 + 未映射清单）
- 台账模板：`references/CARDS-template.md`

- 技能包吸收（包内已是 SKILL.md）→ `skill-pack-absorption`
- 技能怎么写/容量治理/批量替换纪律 → `skill-engineering`
- 情报源抓取 → `intel-source-harvest`
- 脚本模板：`references/report-pack-distillation.md`
