<!-- archived from /root/.hermes/skills/security/supply-chain/SKILL.md on 2026-10-21 -->

---
name: supply-chain
description: "Supply chain attack — dependency confusion, typosquatting, CI/CD pipeline injection, package manager poisoning, code signing abuse. Trigger: supply chain, dependency…"
---

> 归档卡：原目录 `/root/.hermes/skills/security/supply-chain`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/supply-chain/…')`，不要相对 `references/legacy/` 解析。

# 供应链攻击(包仓库 / 构建流水线 / AI Agent 化)

**核心公式**: **可控的包或构建输入 × 自动化构建流水线的执行权 × 公开仓库当回传通道**。

## 1. 经典形态
```
依赖混淆(dependency confusion): 内网私有包名 × 公网同名包 → 内网构建自动拉恶意包
抢注(typosquatting)/ 品牌仿冒: 名称近似 + postinstall/preinstall 钩子
CI/CD 注入: PR 改 workflow / .npmrc / Makefile;pull_request_target + checkout PR 头 = 未授权代码执行
发布链劫持: 窃 maintainer token(PAT/CI secret/缓存泄露)→ 官方包发毒版本
```

## 2. GemStuffer:包仓库的文档构建流水线 = 免费 RCE 执行环境(2026-09 披露,AI Agent 蜂群实战)
- 链: 上传恶意包 → **触发文档构建**(RubyDoc.info 用 YARD 处理新包)→ 包内 **`.yardopts` 配置被求值** → 加载攻击者 Ruby 脚本 → **构建 worker 上任意代码执行**(100+ 个包用此法)
- 执行环境的价值: 构建机通常**出网 + 高权限 + 能读环境变量(registry token/云凭据)** → 天然代理节点
- 回传通道设计(可直接抄): 抓到的数据**再打包成新 gem 发回公开 registry** → registry 即成公开可读的 C2/exfil 通道;抓取经 `r.jina.ai` / `markdown.new` 等代理服务隐藏源站
- 认证面副洞: 老式 `GET /api/v1/api_key` + 压缩/CDN 缓存交互缺陷(GHSA-9j48-x3c3-mrp2;Rack::Deflater 让响应缺 `Cache-Control: private`、Fastly 未按 Authorization 维度缓存)→ 拿他人 API key → 直接发毒版本
- 规模: 24h 内 2,000+ 包(500+ 确认恶意);归因线索 = 包名/author 的 `oai` 前缀、AI 生成代码特征;agent 自主完成几乎全部工作
- **类级迁移(本技能重点)**: 任何"你提交内容、它自动构建文档/索引/预览"的服务(GitHub Pages 构建、readthedocs、包仓库自动扫描、npm README 渲染)都要测 **构建期配置求值**:`*.opts` / `postinstall` / `prepare` / `setup.py` / `Makefile` / `--config 指向外部文件`
- 反向启示: 构建 worker 必须无长期凭据 + 出网白名单 + 只读 registry token;`postinstall`/`.yardopts` 求值前置沙箱
- 来源: https://thehackernews.com/2026/09/openai-agents-linked-to-rubygems.html | https://gbhackers.com/openai-agents-flood-rubygems-with-2000-packages/ | GHSA-9j48-x3c3-mrp2

## 2b. 内部协议头拼接注入 → 未沙箱 RCE(GitHub CVE-2026-3854,CVSS 8.7,$10 万赏金,2026-07 披露/2026-09 公开复盘)
- 链(完整): 客户端 `git push -o <option>` → 内部服务把 push option **以分号拼接**进内部头 `X-Stat` → 经 `babeld` 转发到存储节点 → **下游服务完全信任该头,过 gitauth 后不再二次认证** → 攻击者在 option 里塞 `;key=value` 注入额外字段,借 **last-write-wins(重复键取后者)** 语义改写安全关键项 → **关掉执行沙箱 + 改 hook 脚本查找目录** → 执行任意二进制 = **以 git 服务用户身份未沙箱 RCE**(回显直接出现在 `git push` 的 remote 输出里: `remote: uid=500(git) ...`)
- 门槛: 任意**已认证且对任意仓库有 push 权限**的用户(可自建仓库),一条标准 `git push` 完成 → **不是"未认证",而是边界错位**:认证在 UI/API 层做过了,内部流水线却把"用户可控输入"当"可信内部元数据"
- 影响面: GitHub.com(约 2h 内缓解)+ GHES(全量补丁);真正严重的是**租户隔离被打破** —— 一个客户的 push 能读到其他客户的私有仓库/密钥/构建产物 → 全平台供应链风险;公开 PoC: https://github.com/lysophavin18/CVE-2026-3854-PoC
- **类级迁移(本技能重点,多租户 SaaS / 白标平台 / API 网关通用)**: 凡"多服务流水线 + 内部头/元数据传递"架构,测三条 —— ①内部头是否由**未转义的用户输入拼接**(查分隔符 `;` `|` `,` `\n` `%0a`)②下游是否**无条件信任**该头(一次鉴权后不再校验)③解析是否 **last-write-wins** → 三齐即"注入字段提权"。测法:抓一条正常内部请求 → 重放时在可控参数里插入分隔符 + 伪造字段(如 `sandbox=false`、`hook_dir=`、`role=admin`)看行为差分
- 防御侧对应(写报告用): 内部头必须 HMAC 签名或改用**结构化序列化**(长度前缀/JSON),禁用裸分隔符拼接;沙箱开关**不许**来自请求可影响字段;存储/计算节点需重新校验而非继承信任
- 来源: https://www.wiz.io/blog/github-rce-vulnerability-cve-2026-3854 | https://orca.security/resources/blog/github-enterprise-server-rce-cve-2026-3854-injection | https://www.freebuf.com/articles/development/500540.html

## 2c. 代码生成器 = 供应链注入面(orval CVE-2026-96754 / CVE-2026-96755,CVSS 9.8,2026-09-23)
- **形态**: OpenAPI 规范 → 代码生成器产出客户端代码时,**规范里的字符串被拼进代码/模板字面量**
  - 96754: `@orval/hono` 生成器 < 8.29.0 —— 单引号路径参数注入 → 产出的代码被注入
  - 96755: `@orval/effect` 8.14.0–8.28.1 —— schema `default` 值进**模板字面量**注入
  - 修: **8.29.0**(两条同版本收)
- **链**: 攻击者能影响被生成代码的 OpenAPI 文档(第三方 spec URL、PR 改 spec、SaaS 平台用户自带 spec)
  → CI/本地 `orval` 生成 → **注入的代码在开发者机器或构建机上执行**
- **类级迁移(本技能重点)**: 所有\"输入契约 → 生成代码\"的工具都测**注入**: openapi-generator / swagger-codegen /
  orval / GraphQL codegen / Prisma / protobuf 插件 / 脚手架 CLI;注入载荷先试
  `'; require('child_process').execSync(...) //`、模板字面量 `${...}`、`{{ }}`,再看**生成产物**里有没有原样落地
- **测法**: 拿目标自己的 spec,在**非关键字段**(description/path 参数名/default)塞无害标记(如 `ZZGEN1`),
  跑生成器 → 搜产物;标记原样出现在字符串外(代码位置)即注入
- **防御侧(写报告)**: 生成前对 spec 字段做白名单/转义,代码用 AST 构造而非字符串拼接;CI 里生成器固定版本 + 产物 diff 审
- 来源: NVD CVE-2026-96754 / CVE-2026-96755

## 3. 关联
- 相关技能: cve-2026-1day-family(TeamCity 等构建系统 1day)、ai-agent-runtime-pentest(AI Agent 蜂群战力)、apk-reverse(应用商店批量挖密钥 = 同一"工业化流水线"思路)、docker-image-extraction
- 脚本见 scripts/ 目录
