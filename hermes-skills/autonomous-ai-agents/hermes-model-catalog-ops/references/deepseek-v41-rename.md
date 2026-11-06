# 案例: DeepSeek V4.1 改名,而 Hermes 目录里没有 "v4.1"

会话背景(2026-09-16): 用户问"deepseek 应该是更新了 v4.1 的模型啊,为什么我的 Hermes 里面配置的没有这个模型"。
Hermes 配置: `model.default: deepseek-v4-flash` / `provider: deepseek` / `base_url: https://api.deepseek.com/v1`。

## 原始实测输出(全部为真实执行结果)

### 1) 官方可调用名 —— `GET /v1/models`
```json
{"object":"list","data":[{"id":"deepseek-flash"},{"id":"deepseek-v4-pro"}]}
```
注意: **只有两个**,连 `deepseek-v4-flash` 都不在里面(它是兼容别名)。

### 2) 逐名探测 `POST /v1/chat/completions` (`max_tokens:1`)
| 请求的 name | http | 响应回显 `model` |
|---|---|---|
| `deepseek-chat` | 200 | `deepseek-flash` |
| `deepseek-reasoner` | 200 | `deepseek-flash` |
| `deepseek-flash` | 200 | `deepseek-flash` |
| `deepseek-v4-flash` | 200 | **`deepseek-flash`** ← 兼容路由的关键证据 |
| `deepseek-v4-pro` | 200 | `deepseek-v4-pro`(未改道) |
| `deepseek-v4.1` | 400 | — |
| `deepseek-v4.1-flash` | 400 | — |
| `deepseek-v4.1-pro` | 400 | — |

400 的 body 直接给出权威清单(比翻文档可靠):
```json
{"error":{"message":"The supported API model names are deepseek-flash, deepseek-v4-pro, but you passed deepseek-v4.1-flash.","type":"invalid_request_error","code":"invalid_request_error"}}
```

### 3) 官方文档佐证
- 变更日志(2026-09-10): *"Change the model name to `deepseek-flash` to call the latest V4.1 Flash model. ... for compatibility, the model names `deepseek-v4-flash` / `deepseek-v4-flash-vision-exp` are temporarily routed to DeepSeek-V4.1-Flash."*
- 定价页(脚注): 旧名 "are served by the DeepSeek-V4.1-Flash model and billed at the Flash price";V4 Pro 在 2026-09-14 之后**继续供应**(9/9 新闻说要改道,9/10 变更日志改口 ⇒ 实测确认 `deepseek-v4-pro` 仍返回自身)。
- 峰谷: off-peak = 峰价 50%;峰时段 UTC 01:00-04:00 / 06:00-10:00 周一至五 = 北京 09:00-12:00 / 14:00-18:00。

### 4) Hermes 侧三层根因(全部实测)
**a. provider 插件白名单陈旧**(Hermes 构建日期 8/24,插件停在 4 月的 V4 命名)
```python
# plugins/model-providers/deepseek/__init__.py
fallback_models=("deepseek-v4-pro", "deepseek-v4-flash")
default_aux_model="deepseek-v4-flash"
```

**b. 选择器磁盘缓存陈旧**
```json
// profiles/123/provider_models_cache.json
"deepseek": {"fp":"c0db6950e6a28c8e","at":1789567723,"models":["deepseek-v4-pro","deepseek-v4-flash"]}
```

**c. 名字规范化(最隐蔽的一层)** —— 配置里写什么 ≠ 上线发什么
```
deepseek-flash                   -> deepseek-v4-flash      # 新一等名被兜底改回旧名
deepseek-v4-flash                -> deepseek-v4-flash
deepseek-v4-pro                  -> deepseek-v4-pro
deepseek-v4.1-flash              -> deepseek-v4.1-flash    # 正则放行 → 直送 → 400
deepseek-v4.1                    -> deepseek-v4.1
deepseek-chat                    -> deepseek-v4-flash      # 退役别名被改写
deepseek-v4-flash-vision-exp     -> deepseek-v4-flash-vision-exp
```
正则: `_DEEPSEEK_V_SERIES_RE = ^deepseek-v\d+([-.].+)?$`
兜底: `_normalize_for_deepseek()` 的 `return "deepseek-v4-flash"`(一切不认识的都落到这里)。

### 5) 修复动作(无交互刷缓存,已验证)
```bash
cd ~/AppData/Local/hermes/hermes-agent && HERMES_PROFILE=123 python - <<'EOF'
import sys, json; sys.path.insert(0,'.')
import hermes_cli.models as M
print("return:", M.cached_provider_model_ids("deepseek", force_refresh=True))
print("ondisk:", json.dumps(json.load(open(M._provider_models_cache_path(),encoding="utf-8")).get("deepseek"), ensure_ascii=False))
EOF
```
输出:
```
return: ['deepseek-v4-pro', 'deepseek-v4-flash', 'deepseek-flash']
ondisk: {"fp": "5534243cd4d10411", "at": 1789567752, "models": ["deepseek-v4-pro","deepseek-v4-flash","deepseek-flash"]}
```
`deepseek-flash` 就此进入 picker / `/model`。注意 curated 在前、live 在后追加 → 新名排末尾。

## 用户可见结论模板(本次实际交付的形状)
1. **先给结论,反直觉但不含糊**: "DeepSeek 根本没有叫 v4.1 的模型串,而你现在其实已经在跑 V4.1 了。"
2. 给实测表格(请求名 / http / 回显 model),不给推断
3. 三层根因用表格列,每层带证据文件路径
4. 明确说"改 config 零收益"+ 理由(normalize 会改回去),并给出**唯一会出错的填法**(`deepseek-v4.1-flash` → 400)
5. 说明已做了什么(刷缓存)+ 需要用户决定的事(要不要打补丁)
6. 顺手给省钱信息(峰谷时段换算到北京时间)
7. 未验证的事明确标注未验证(如 vision 能力表没查)
