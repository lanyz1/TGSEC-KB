# 按「嵌入组件 / 框架指纹」做引擎 fan-out —— 现成查询矩阵

§1 的优先级表里**排第一位的就是「共享第三方平台指纹」**(同客服平台域名、同 captchaId、同静态资源 hash)。
本文件把这件事的**现成查询表**沉淀下来,不用每次重新想词。

通用规则(任何组件类型都适用):

1. **一个组件域 / 一个框架标题 = 一条查询,不要用 `or` 合并** —— 分档查才能分档交付,
   也才能看出哪一档其实是 0 条(静默 0 条多为额度/语法问题,不是真空集)。
2. **两类语法分开用**:组件自身域名/路径 → `body:`;**站点标题** → `html_title:`。
3. **`body:` 全文查询是额度杀手**(响应最大、最慢),先跑一条探价值再排队;
   第一条就没产出 ⇒ 该引擎对这一档覆盖不够,别把额度烧完才承认。
4. 命中量千级是常态,**page_size 取 15 就够交用户核授权**,不要拉全量。

---

## A. 在线客服 / 聊天组件(→ 实体商业站,不是技术人 demo)

```
host.services.endpoints.http.body:"53kf.com"        # 53客服(中文站最常见)
host.services.endpoints.http.body:"zoosnet.net"     # 商务通
host.services.endpoints.http.body:"meiqia.com"      # 美洽
host.services.endpoints.http.body:"qiyukf.com"      # 网易七鱼
host.services.endpoints.http.body:"sobot.com"       # 智齿
host.services.endpoints.http.body:"7moor.com"
host.services.endpoints.http.body:"kuaishangtong.com"
host.services.endpoints.http.body:"easemob.com"     # 环信
host.services.endpoints.http.body:"tawk.to"
host.services.endpoints.http.body:"livechatinc.com"
```

这一档命中回收/加盟/代账/批发/制造业官网之类**真实经营主体** —— 用户最容易对上「这家我熟」。

## B. 自部署 AI / 客服框架(→ 独立数据面 + `/api/*` 授权面)

```
host.services.endpoints.http.html_title:"Dify"
host.services.endpoints.http.html_title:"FastGPT"
host.services.endpoints.http.html_title:"RAGFlow"
host.services.endpoints.http.html_title:"Langflow"
host.services.endpoints.http.html_title:"Flowise"
host.services.endpoints.http.html_title:"Open WebUI"
host.services.endpoints.http.html_title:"LibreChat"
host.services.endpoints.http.html_title:"AnythingLLM"
host.services.endpoints.http.html_title:"Chatwoot"
host.services.endpoints.http.html_title:"Typebot"
host.services.endpoints.http.html_title:"Botpress"
```

同族思路可平移到任何自部署面板(宝塔、Grafana、WordPress 后台、低代码后台)。

## C. 基础设施端口档(脏,放最后)

```
host.services.port=11434   # Ollama 默认口(/api/version、/api/tags 未授权)
host.services.port=7860    # Langflow / Gradio
host.services.port=4000    # LiteLLM
host.services.port=6333    # Qdrant
host.services.port=2718    # marimo(未授权完整 PTY)
```

同端口非目标服务的误命中多;额度紧张时直接砍掉这档。

---

## 命中判读(哪几条先递用户看)

| 命中形态 | 含义 | 排序 |
|---|---|---|
| 裸标题直出平台名(`Dify` / `FastGPT`) | 首页未设认证的可能性高 | 优先给用户 |
| `Sign in - X` / `401 Unauthorized` | 已开登录页 | 仍算候选(认证面本身是攻击面) |
| `X 账号管理` / `X 训练数据下载` 直出 | 管理面/数据面暴露 | 重点标出 |
| 证书露 `kube-apiserver` / `192.168.x.x` / `宝塔面板` / `MySQL_*_Auto_Generated_CA` | 自签内网证书 = 自建自维护,大概率无专业运维 | 重点标出 |
| `301 / 404 / 502` + 平台名 | 路径在、服务挂了或反代配错 | 记录,不急 |

**证书字段必须收进清单**:`cert.parsed.subject_dn` + `dns_names` 直接给出**域名和内网主机名** ——
用户认授权看的是域名,不是裸 IP。`domains` 列不能省。

---

## 额度断档时怎么交(常态,不是脚本 bug)

不要沉默,也不要假装扫完了。汇报里写清:**已采到多少 / 哪几档采到了 / 哪几档一条没采**,
同时把**已到手的那批**先交付给用户核授权(半份清单也有用),并把两个选项一起递过去:
换免费源续扫,或用户补 key 后原样重跑缺的那几档。
把半份清单说成「扫完了」比没扫更糟:用户会据此核授权,漏掉的维度永远不会被补。
