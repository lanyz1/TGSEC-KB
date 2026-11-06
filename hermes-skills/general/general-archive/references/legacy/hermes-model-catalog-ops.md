<!-- archived from /root/.hermes/skills/autonomous-ai-agents/hermes-model-catalog-ops/SKILL.md on 2026-10-21 -->

---
name: hermes-model-catalog-ops
description: "Hermes 里没有某模型/模型改名没同步时用: 实测API拿权威名+三层目录排查。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, model-catalog, provider, model-name, picker-cache, normalize, deepseek, config]
---

> 归档卡：原目录 `/root/.hermes/skills/autonomous-ai-agents/hermes-model-catalog-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/autonomous-ai-agents/hermes-model-catalog-ops/…')`，不要相对 `references/legacy/` 解析。

# Hermes 模型目录与模型名运维

任何 provider 改名 / 退役别名 / 新模型上线后,"我的 Hermes 里为什么没有这个模型"这类问题的**排查与同步**作业。

## 触发场景
- 用户问:"XX 更新了新模型,为什么我的 Hermes 里配置的没有?"、"模型选择器里看不到 X"
- 配置里的模型名和 provider 官方文档对不上
- 想知道"我到底在跑哪个版本的模型"
- 需要在不改 config / 不打补丁的前提下让新模型可选

## 0. 铁律:先实测 provider,再谈 Hermes
**永远不要从新闻稿、搜索摘要或记忆里确定模型名。** 搜索到的"新模型名"经常是 SEO 农场编的(本次 `deepseek-v4.1-flash` 就是虚构的)。

两个权威来源,都来自 provider 自己:
1. `GET <base_url>/models` —— 官方可调用名(注意:可能**不是**完整集合,provider 会藏兼容别名)
2. **调用一个不存在的名字,400 的 message 会枚举当前所有合法模型名** —— 这是最快的权威清单,比翻文档可靠

```bash
# 一次性拿到 /models 清单 + 逐名探测(含 400 枚举消息 + 200 的 model 回显)
bash scripts/probe-model-names.sh https://api.deepseek.com/v1 "$DEEPSEEK_API_KEY" \
  deepseek-flash deepseek-v4-pro deepseek-v4.1-flash
```
> curl 输出**不要写 `/tmp`**: 本机 curl 是 native Windows 程序,不认 MSYS 的 `/tmp`(写了会 "No such file or directory")。用 `$LOCALAPPDATA/Temp`。

## 1. "看不到模型"有三层独立原因,要逐个查
| 层 | 位置 | 症状 |
|---|---|---|
| provider 插件白名单 | `plugins/model-providers/<p>/__init__.py` 的 `fallback_models=()` | 名字是官方几个月前的老命名,新名不在其中(live 拉取失败时 picker 只显示这些) |
| 选择器磁盘缓存 | `<HERMES_HOME>/provider_models_cache.json` 的 `<provider>` 行 | 缓存里只有旧名 → picker / `/model` 里没有新名 |
| **名字规范化** | `hermes_cli/model_normalize.py` | **config 里写的名字 ≠ 上线发出的名字**(最容易漏的一层) |

`<HERMES_HOME>` 就是活跃 profile 目录(`profiles/<name>/`),不是 `~/.hermes` 根目录。

## 2. 判据:配置名 vs 上线名(config 改不改,取决于这一条)
```bash
cd ~/AppData/Local/hermes/hermes-agent && python - <<'EOF'
import sys; sys.path.insert(0,'.')
from hermes_cli.model_normalize import normalize_model_for_provider as n
for m in ["deepseek-flash","deepseek-v4-flash","deepseek-v4.1-flash","deepseek-chat"]:
    print(f"{m:32s} -> {n(m,'deepseek')}")
EOF
```
- 若新名被改写成旧名 → **改 config 零收益**(wire 完全一致),如实告诉用户"你已经在跑新模型了",别为了动作好看改配置
- 若名字被**原样放行**但 provider 不认 → 会直接 400,见下面的正则坑

**兼容路由**: provider 常把旧名临时路由到新权重。判断"是否真在用新模型"看 **200 响应体里回显的 `model` 字段**,不看请求名。
DeepSeek 实例: 请求 `deepseek-v4-flash` → 响应 `"model":"deepseek-flash"` ⇒ 已经在跑 V4.1-Flash 权重。

## 3. 刷缓存:走 Hermes 自己的代码路径
不要手改 JSON,也不要依赖交互式 `hermes model --refresh`(picker 会阻塞会话):
```bash
cd ~/AppData/Local/hermes/hermes-agent && HERMES_PROFILE=<profile> python - <<'EOF'
import sys, json; sys.path.insert(0,'.')
import hermes_cli.models as M
print("path  :", M._provider_models_cache_path())
print("return:", M.cached_provider_model_ids("deepseek", force_refresh=True))
print("ondisk:", json.dumps(json.load(open(M._provider_models_cache_path(),encoding="utf-8")).get("deepseek"), ensure_ascii=False))
EOF
```
必须同时打印 return 和 ondisk —— 只有 ondisk 里出现新名,才算真的刷进去了。

picker 的最终列表 = `curated(_PROVIDER_MODELS 或 profile.fallback_models)` 与 `live /models` 的**并集**(`_LIVE_FIRST_PICKER_PROVIDERS` 里的 provider 才是 live 优先)。所以 curated 陈旧只影响排序,新名靠 live 补进来。

## 4. 正则坑(会静默放行假名字)
Hermes 的 V 系列放行正则: `^deepseek-v\d+([-.].+)?$`
- `deepseek-v4.1-flash` / `deepseek-v4.1` **匹配** → 原样上线 → provider 400
- **不要把猜测出来的名字写进 config**;名字只能来自实测

## 5. 要打补丁就成套打,半套比不打更糟
想"名正言顺"用新一等名,要同时改**两处**(只改第一处会踩坑):
1. `hermes_cli/model_normalize.py` 的 `_DEEPSEEK_CANONICAL_MODELS` —— 否则被兜底改回旧名
2. `plugins/model-providers/<p>/__init__.py` 的能力判定,例如 DeepSeek 的
   `_model_supports_thinking()` 判据是 `m.startswith("deepseek-v")`,**`deepseek-flash` 不匹配**
   → `extra_body.thinking` 不被显式声明 → DeepSeek 默认 thinking ON → 撞上
   `reasoning_content must be passed back` 的 HTTP 400(#15700/#17212/#17825)

默认动作:**不打补丁**,先给用户"线上请求零差异"的结论,让用户决定。真要打,改完必须跑 normalize 自测 + 该 provider 插件的测试。

## 6. 顺手交付(用户会用到)
- **峰谷价换算到本地时区**。DeepSeek off-peak 是峰价 50%;峰时段 UTC 01:00-04:00 / 06:00-10:00 周一至五 = **北京时间 09:00-12:00 / 14:00-18:00** ⇒ 长跑 agent 任务丢到晚上/凌晨跑省一半。
- `model.base_url` 与 key 的真实来源:`hermes config get model` + profile 的 `.env`(profile 的 `.env` 优先于根 `.env`)。
- 会话内切换: `/model <name>`(会话级),`hermes config set model.default <name>`(持久)。

## 坑
1. `/v1/models` **不是**完整可调用集合:DeepSeek 只返回 `deepseek-flash` / `deepseek-v4-pro`,但 `deepseek-v4-flash`、`deepseek-chat`、`deepseek-reasoner` 都还能 200(兼容路由)。权威集合 = live ∪ curated ∪ 兼容别名,靠逐个 probe 的 400 消息确认。
2. 缓存写的 `fp` 是**凭据指纹**:换 key / 换 profile 会让缓存行失效重拉,看到 `fp` 变了不是缓存坏了。
3. 别把内存/技能库里硬编码的模型名当事实,provider 改名很频繁(本次 DeepSeek 2026-09-10 改名,而 Hermes 8/24 构建的插件白名单还停在 4 月的 V4 命名)。
4. 交付给用户的结论必须区分**已验证**与**未验证**(如"vision 路径能否直接吃新模型"没查就明说没查)。

## 代码地图(排查用)
- `hermes_cli/model_normalize.py`: `normalize_model_for_provider()`、`_normalize_for_deepseek()`、`_DEEPSEEK_V_SERIES_RE`
- `hermes_cli/models.py`: `provider_model_ids()`(curated ∪ live 合并)、`cached_provider_model_ids()`、`_provider_models_cache_path()`
- `plugins/model-providers/<p>/__init__.py`: `ProviderProfile`(`fallback_models`、`default_aux_model`、`build_api_kwargs_extras`)
- `providers/base.py`: `fallback_models` 语义("live fetch 失败时 picker 显示的 curated 列表")
- 随 Hermes 附带的 `hermes-agent` 技能 → `references/providers-and-models.md`(provider/别名总表;该技能受保护,只读)

## 验证
1. `probe-model-names.sh` 的 400 枚举消息里出现目标名字
2. `normalize_model_for_provider(名字, provider)` 返回的就是那个名字(否则 wire 上是别的)
3. `provider_models_cache.json` 的 ondisk 列表含新名
4. 端到端: 用该名字发一次真实 completion,响应 `model` 字段符合预期

## 参考文件
- `references/deepseek-v41-rename.md` —— DeepSeek V4.1 改名完整案例(原始实测输出 + 三层根因 + 用户可见结论模板)
- `scripts/probe-model-names.sh` —— 一次性拿 provider 权威模型名清单 + 逐名探测
