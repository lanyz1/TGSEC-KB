<!-- archived from /root/.hermes/skills/security/source-informed-endpoint-audit/SKILL.md on 2026-10-21 -->

---
name: source-informed-endpoint-audit
description: "Use when target source is available to map routes and auth."
---

> 归档卡：原目录 `/root/.hermes/skills/security/source-informed-endpoint-audit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/source-informed-endpoint-audit/…')`，不要相对 `references/legacy/` 解析。

# Source-Informed Endpoint Audit

手上已经有目标源码时，**先把路由表和鉴权覆盖面读出来**，再回头做黑盒测试。黑盒猜路径只会得到无信息的 404，而源码能直接把“这条路死在哪一层”写成可引用的判据。

## 何时用

- 目标指纹匹配某个开源项目（可直接拉 upstream 对照）
- 已拿到源码泄露：`.git` 目录、备份包、容器内文件、source map
- 黑盒反复 404/405，不确定是路径错了还是路由真不存在
- 需要给“为什么这条路打不通”出**可复核的结论**，而不是“试过没反应”

## 流程（按序）

### 1. 定位路由注册文件

按栈找（详见 `references/route-locations-by-stack.md`）：
Go/Gin → `routes/*.go` + `SetupRouter`；Laravel → `routes/web.php` `api.php`；Spring → `@RequestMapping`；Express → `router.*`。

### 2. 先画鉴权覆盖面，再看单个端点

关键不是“这个端点有没有鉴权”，而是**它在哪个 group 里注册、那个 group 有没有 `.Use(auth)`**。逐个 group 读 `Use` 链，再把路由挂载点对上去。**注册在鉴权 group 之外的路由＝未鉴权**，哪怕它长得像后台接口。

### 3. 精确到 method + path，绝不猜

从注册表拿到真实路径（空路径挂载很常见，如 `user.PUT("", h)` 实际是 `PUT /api/v1/user`）。猜路径拿到的 404 不能证明任何鉴权结论——它只证明路径错了。

### 4. 读鉴权中间件源码，列出**所有**被接受的凭证形态

中间件常常同时接受多种：header API key、JWT、query token、WebSocket subprotocol。每种都要单独试过才算覆盖。记录每种的比较原语（`ConstantTimeCompare` / `==` / 解密后比对）。

### 5. 追到密钥生成处，死路才算**证成**

顺着比较点找到密钥的来源：启动时随机、环境变量、配置文件、密钥派生。落到**代码生成点**才能下结论：

- `crypto/rand` 生成 256 位 → 离线爆破是**信息论死路**，换策略也绕不过
- 启动时随机 secret（重启即变）→ 无法伪造
- 弱比较 / 缺类型混淆 / 空值跳过 → 才是可绕的信号

没有指到生成点的“高熵所以打不通”只是猜测，不写进报告。

### 6. 能力令牌型未鉴权路由：读它的令牌格式

注册在鉴权 group 外、但路径里带 `:token` 的路由（静态资源/插件 UI/短时能力 URL），去看令牌怎么签：带用途前缀的 AEAD、带签名的 claims。**加密签名令牌 = 不可伪造**；若签名可预测、缺过期校验、或密钥与别处共用，直接追。

## 常见坑

- **猜路径当测试**：先用注册表拿准路径，再发请求。反过来做会浪费轮次，并让“404”污染结论。
- **把 404 当“已保护”**：404 只说明路由不存在，与鉴权无关。
- **共享密钥没被当成放大面**：同一把 key 既是 AEAD 密钥又是 HMAC 签名密钥时，一处泄露同时废掉两条路——报告里合并陈述，别拆成两个小发现。
- **工具/脚本出错 ≠ 资产没了**：脚本报错先读错误信息改写法；确认是技术死路后**不要**因为脚本 bug 去修复重跑。
- **白盒结论要能复核**：每个“已堵死”的结论标注 `文件:行号`，方便委托人自己验。

## 与其他技能的关系

- `hunt-api-misconfig` / `hunt-idor`：白盒定位到未鉴权端点后，交给它们做利用
- `code-audit`：需要逐行数据流分析时用那个
- `related-domain-pivot`：先用那个确认“多入口是不是一个后端”，再在这里读鉴权

## 支持文件
- `references/route-locations-by-stack.md` — 各技术栈的路由/鉴权代码位置速查
