# 认产品：黑盒后台 → 商业产品 → 厂商/卖家

**什么时候用**：目标是被加固到「注入死、鉴权严、无源码、无默认口令」的后台，且 `/openapi.json` / 页面文案显示它是**别人做的商业产品**（代理商字段、通用导航、通用提示语）。

**为什么值得做**：这类目标是同一份产品做成千上万次部署，厂商手里必然有默认口令、`SECRET_KEY` 推导方式和已知缺陷；同时**同产品的其它部署**里常有一个弱配置的（换过默认口令之外的、调试开着的、测试环境），打穿它能反过来验证产品行为。

## 步骤

### 1. 从目标自身的 API 契约挖产品名与运营者身份

`/openapi.json` 的 `components.schemas` 里，**字段默认值/示例值经常写死真实值**——默认联系 TG 号、默认品牌名、默认域名、默认计量参数：

```bash
curl -s https://<host>/openapi.json | python3 -c "
import sys,json; d=json.load(sys.stdin)
for n,s in d.get('components',{}).get('schemas',{}).items():
    for f,v in (s.get('properties') or {}).items():
        if isinstance(v,dict) and v.get('default') not in (None,''):
            print(n,f,'=',v['default'])"
```

默认值里出现 `@<handle>` 之类联系方式 = 产品名 + 运营者 TG 号一次到位（本类案例中后台的 `clone_contact` 默认值直接就是运营者的号，同时证明这是**代理商视角**的后台）。顺带把 `Body_<func>_<path>_post` 这类 schema 名收下来——FastAPI 自动命名里带内部函数名，能反推未在 `paths` 列出的端点，也用于判「同款产品」。

### 2. TG 功能频道是最快确认产品形态的地方（无需登录）

`t.me/s/<handle>` 是公开预览页，**带浏览器 UA 直接 curl 即可**，不需要 TG 账号、不走 API：

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
curl -sL --max-time 25 -A "$UA" "https://t.me/s/<handle>" -o /tmp/tg_ch.html
```

正文在 `div.tgme_widget_message_text` 里，用正则切块去标签即可（`<br>` → 换行后再 `re.sub(r'<[^>]+>','')`）。

一次把候选 handle 全跑：**厂商频道**（产品名/品牌词）、**卖家客服 bot**、运营者自己的号、以及产品文档里提到的**自助克隆 bot**。实测：运营者的私人频道常常没有公开预览（返回空页 / 302），而**厂商的功能说明频道一定有**——所以先打厂商，从它里面反查运营者与产品版本。

### 3. GitHub 仓库搜索（免登录那条路）

```bash
curl -s -H "Accept: application/vnd.github+json" -H "User-Agent: research" \
  "https://api.github.com/search/repositories?q=$(python3 -c "import urllib.parse;print(urllib.parse.quote('<中文关键词>'))")&sort=stars&per_page=20"
```

用中文产品名/功能词（`记账机器人`、`多群网页账单`、`克隆记账`）而不是错误串搜——收录的是仓库描述，错误串不在里面。

搜索结果按「是不是同一份产品的族谱」筛：文件树里有没有目标的**路由/字段名**（如 `admin_auth`、`/admin/instances`、`token_hint`）。**不同语言栈的同族产品不要硬套默认口令**（PHP/ThinkPHP 的记账面板口令与 FastAPI 面板无关）。

### 4. 代码级搜索与中文搜索的选路

- 代码搜索：`grep.app`、`searchcode.com`、Sourcegraph 对机房 IP 常返回挑战页/404，**不要在这里耗调用**；GitHub 代码搜索 API 需要 token（无 token 时只有仓库搜索可用）。错误串搜不到 ≠ 产品不存在，换成中文功能词走仓库搜索与通用 web 搜索。
- 通用 web 搜索优先用**中文查询**（产品名 + 功能词），并且**别信 SEO 站**：中文搜索这类词会撞上一堆「算账机器人」刷量站，它们只是导流，不含源码。
- 中文源码站（`xxx源码`、`yybots.com` 一类）几乎都是付费/登录墙。**列为不可行，不要反复试**；真正能拿到源码的路径只有：厂商频道里公开的版本说明、卖家给你的可二开包、或者已泄露的仓库。

## 源码/默认值到手后看什么（按性价比）

1. 管理员**创建**逻辑：是交互式脚本还是硬编码默认？有没有 `SECRET_KEY` / cookie 签名密钥的**推导公式**（`sha256(bot_token)`、`hmac(secret, ...)`、固定 salt）——这决定 cookie/token 伪造是否可行。
2. 签名校验顺序与 scope：`group 存在 → expires → sig → scope` 这类顺序决定了哪些参数能当预言机，哪些先于验签。
3. 登录/限流的 key：按 IP 还是按用户名（决定喷法），以及是否存在 admin_id/token_version 之类的记录级校验（差分预言机）。
4. 未在 `/openapi.json` 列出的端点（schema 名反推 + 源码路由表）：回调、webhook、内部 API 常常漏鉴权。

## Pitfalls

- **认产品的产出是「源码/默认值」这条路径，不是聊天跑题。** 汇报时要一句说清「产品是什么、厂商是谁、为什么默认口令不在字典里」，并把仍在跑的字典进程一并交代——否则用户会以为你在离题。
- 不要为了拿测试实例去注册厂商的试用/克隆服务：那需要 TG 账号与交互，属于社工路线，需要用户明确授权后再走。
- 产品身份结论要**同时**用于两件事：去厂商侧找默认值/源码，以及在**同产品的其它部署**上找弱配置（同一份代码，防护水平差别巨大）。
