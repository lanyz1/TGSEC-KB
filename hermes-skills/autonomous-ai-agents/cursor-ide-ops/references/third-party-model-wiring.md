# 接第三方模型:判性质、接线、换 key

## 1. 先判报错是谁发的(决定还有没有戏)

```bash
grep -c "<报错原文>" "<Cursor安装>/resources/app/out/vs/workbench/workbench.glass.main.js"
```

客户端搜不到 = 服务端校验。实测:`Model name is not valid` 不在客户端代码里 →
服务端不认这个模型名,自定义模型这条路上该版本走不通。

从客户端代码里能捞到的相关字符串(证明这个功能存在、且需 Pro):

```
"Override OpenAI Base URL"
"Change the base URL for OpenAI API requests."
"Add model to switcher"
"Requires pro (custom model). "
```

## 2. 接线(缺一不可)

Settings(`Ctrl+Shift+J`)→ **Models**:

1. `OpenAI API Key` 填**目标服务商的 key**(不是 OpenAI 的)
2. **`Override OpenAI Base URL` 开关必须打开** → 填对方 OpenAI 兼容端点
   只填 key 不填这个 → 拿新 key 去请求官方 → 必失败
3. `Add model to switcher` 加模型名 —— 必须与服务商 `/v1/models` 返回的**完全一致**
4. **关掉其它 OpenAI 模型**(GPT-4o / o1 / o3 / gpt-5)→ 不漏必失败

## 3. 先在命令行验,再点界面

```bash
curl -s -H "Authorization: Bearer $KEY" https://<端点>/v1/models
# {"object":"list","data":[...]} = key 有效
```

发最小对话请求时用 python 构造 JSON —— **直接在 bash 里拼带中文的 JSON 会被编码搞坏**,
报 `invalid unicode code point`,那不是 key 的问题。

## 4. 端点速查

多数兼容服务同时提供两种格式,按客户端选:

| 格式 | 路径后缀 | 给谁用 |
|---|---|---|
| OpenAI 兼容 | `/v1`(如 `https://api.deepseek.com/v1`) | 绝大多数客户端、Cline、各类 IDE 插件 |
| Anthropic 兼容 | `/anthropic` | Claude Code 那类 |

两种都返回 401 时别慌 —— **401 = 服务器可达、只是没带 key**,地址是对的。

## 5. 可靠备选:插件(Cline)

```bash
<Cursor安装>/resources/app/bin/cursor --install-extension saoudrizwan.claude-dev
```

首次引导选 **Bring my own API key**(不要选 Login / 免费额度)。

| Cline 字段 | 值 |
|---|---|
| API Provider | **OpenAI Compatible** |
| Base URL | `https://api.deepseek.com/v1` |
| Model ID | 与服务商 `/v1/models` 一致 |
| API Key | 第三方 key |

- 规则放 **`.clinerules/*.md`**(自动加载),**不要**指望它读 `.cursor/rules/`
- 第一句验证:「读一下 .clinerules/<规则文件>,用 5 行说明作业流程」
  能准确复述 = 规则加载 + 模型接通都成功
- **快捷键绑定写的是 mac 的 `cmd`** → Windows 上失效,只能用命令面板或点图标

## 6. 换 IDE 里存的 API key

```python
import sqlite3, shutil, time
DB = r"...\state.vscdb"
shutil.copy2(DB, DB + ".bak_" + time.strftime("%Y%m%d_%H%M%S"))   # 必做
con = sqlite3.connect(DB); cur = con.cursor()
cur.execute("UPDATE ItemTable SET value=? WHERE key='cursorAuth/openAIKey'", (new_key,))
con.commit()
```

- **改前必须完全关闭应用**
- 键名靠枚举:`SELECT key FROM ItemTable` 里含 `apiKey|openai|model|baseurl` 的项
- 实测 Cursor 3.x **不在本地存 base URL** —— 那一步只能让用户在 UI 里点
- 改完先命令行验证 key,再让用户开应用

## 7. 排查「key 明明填了却报错」的顺序

1. key 本身有效吗 → `curl` 直测端点
2. base URL 填了吗、开关打开了吗 → 只填 key 必失败
3. 官方模型开关关了吗 → 不关必失败
4. 上面都对还报模型名无效 → 服务端校验,换插件路径
