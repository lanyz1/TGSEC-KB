---
name: oss-version-patch-diffing
description: "Use when a target runs a known OSS product; diff tags."
version: 1.0.0
tags: [pentest, fingerprint, version, patch-diff, github, oss]
---

# OSS 版本差分预言机 (Version-Patch Diffing)

目标跑的是**已知开源产品**时（发卡站/商城/CMS/面板/框架——独角数卡、Dcat、WordPress、宝塔、若依…），别先去翻 PoC 库：**先钉死版本，再拉相邻 tag 的官方差分**。那串 diff 就是「这个部署缺了哪些安全补丁」的精确清单，比漏洞库检索更快、更准，而且不会拿错 CVE。

## 一、钉版本（先钉，再打）

按可信度排序：

1. **页面 footer / 后台仪表盘**：中文商业系统常直接明文写 `产品名 Vx.y.z`（独角数卡实测 footer 就有 `独角数卡 V2.0.5`）。
2. **静态资源指纹**：`/assets/<theme>/...`、`?v=x.y.z`、JS/CSS 里的构建号、主题名（`luna` 等主题只存在于某版本之后）。
3. **框架/依赖版本**：后台框架（Dcat Admin、AdminLTE）版本 + Cookie 名（`id5_session` 之类 = 项目标识 + session 名）。
4. **行为指纹**：路由存在性、报错文案、字段名、默认路径（见 §五）。

> 禁止用「功能像不像」猜版本 —— 会拿错补丁，整轮白打。

## 二、取差分

```bash
# 1) 认 tag 名（GitHub 无鉴权可用；配额紧就换镜像/代理）
curl -s "https://api.github.com/repos/<owner>/<repo>/tags?per_page=40"

# 2) 拿紧凑补丁（比 JSON 好读得多；用 diff media type）
curl -s -H "Accept: application/vnd.github.v3.diff" \
  "https://api.github.com/repos/<owner>/<repo>/compare/<旧tag>...<新tag>"

# 3) 只要文件清单
curl -s "https://api.github.com/repos/<owner>/<repo>/compare/<旧tag>...<新tag>" | \
  python3 -c "import sys,json;print('\n'.join(f['filename'] for f in json.load(sys.stdin)['files']))"
```

先看 **CHANGELOG / release notes**：`修复XX漏洞`、`安全更新`、`fix security` 这类条目直接点名了要打什么，再去 diff 里找那行补丁。

## 三、读差分：补丁即地图

在 diff 里优先盯这几类新增行——它们就是**本部署缺失的防线**：

- **新加的归属/来源校验**：`if ($x->handler != '/pay/foo') return 'fail';` ⇒ 没这行的版本里，**每个同类入口**都能被跨用（拿 A 的凭据打 B 的接口）。
- **新加的权限/角色判断**、`abort(403)`、中间件挂载 ⇒ 对应端点在旧版是裸的。
- **密钥/签名材料的更换**：从弱字段（`merchant_id`、短 id、公开 pid）换成强随机 ⇒ 旧版**用公开值当签名密钥**，可直接离线自算。
- **签名/金额/幂等校验的补全**：旧版可能只比一个字段，或完全不校验金额。
- **参数来源的收紧**：`从请求取` → `从会话/DB 取` 是重点（旧版可越权指定对象）。

## 四、⚠️ 读源码必须按 tag，禁读 master（本类最贵的坑）

拿 master/默认分支审旧版目标 = 在读**已经修补过的**代码，必然得出「**不可利用**」的错误结论，并把它写进报告。

- **症状自查**：补丁明明改了函数 F，你在 master 上看 F 却觉得「校验齐全、打不动」→ 你读错版本了。看到这个症状，立刻换 tag 重读。
- 取源码固定写成：`https://raw.githubusercontent.com/<owner>/<repo>/<TAG>/<path>`。**每次都要带 tag**；旧 tag 里没有该文件时，退到最近的旧 tag，不要顺手用 master 顶替。
- 真实代价：独角数卡案例——用 master 审 2.0.5 目标，把「支付通道混淆」判死（报告写成「仅配置 yipay、无弱密钥网关 ⇒ 不可利用」）；改 `compare/2.0.5...2.0.6` + 按 tag 重读后，一击实现 0 元购发卡。

## 五、拿不到源码/版本对不上时的退化打法

拉最近几个 tag 的**路由表（`routes/*.php`、`urls.py`、`Router`）与默认配置**，与目标的**可观测行为**做差分指纹：

| 观测 | 推断 |
|---|---|
| 路径 405（`Allow: GET`）而另一版本是 ANY | 该版本的路由定义形态 |
| 401 vs 403 的取舍、报错文案 | 中间件/校验是哪个版本引入的 |
| 字段名差异（`captcha` vs `captcha_code`） | 前端与后端版本区间 |
| 新路由 404 ⇒ 版本早于引入它的 tag | 版本上界 |

## 六、坑速查

- `compare/<a>...<b>` 两个 tag 都必须存在；轻量 tag 与 annotated tag 名可能不一致，先 `tags` 接口确认拼写。
- 无鉴权 GitHub API 限流（~60/h）⇒ 一次把 tags + compare 拉全，别在循环里反复打。
- diff 里大量噪音（README/翻译/依赖升级）：先 `grep '^diff --git'` 拿文件清单，再只看业务目录。
- 版本差分只产出**候选**：真洞仍需按确认门跑出可复现证据（VALIDATED）才进高危报告。
- 同族产品补丁可横向复用：A 产品的「回调归属校验」补丁，往往对应 B 产品的同一类洞。

## 七、案例

- 独角数卡 (dujiaoka) ≤2.0.5 支付通道混淆 → 0 元购发卡：`card-merchant-platform-pentest` §六（打法）＋ §七（差分预言机细节）＋ `references/dujiaoka-205-channel-confusion.md`（密钥矩阵、完整链、修复建议）。
- 目标类技能：`card-merchant-platform-pentest`（发卡/号商）、`pentest-execution`（开局矩阵，user-owned，改动需 `hermes curator adopt`）。
