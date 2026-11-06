# 全局登录过滤器 + 白名单枚举法;以及移动端包是**独立(且常更松)**的接口面

> 2026-09 灰豚数据实战。适合:目标是一个 JSON API(非传统后台),不分端点地返回
> "登录状态已失效",你想知道**到底哪些端点不用登录**;以及你想找**第二套接口面**。

## 1. 全局过滤器长什么样(先定性,别急着测漏洞)

未登录时打**任意**端点都返回**同一个**信封,只有少数路径例外:

```json
{"status":200,"message":null,"time":null,"total":0,"code":-200,"data":null,...,"encrypt":false,"version":"2026-07-01"}
```

⇒ 是"全局过滤器 + 路径白名单"模型(常见于 Spring `HandlerInterceptor` + 白名单配置),
不是每端点各自鉴权。**白名单就是未授权面** —— 把它枚举出来就是收益。

## 2. 枚举法(一次把全站打完,自己给自己分类)

1. **拿全端点**:见 `vite-spa-recon.md` / `vue-webpack-spa-recon.md` / `umi-*`;本次 PC 端 umi 包一次给出 1,340 条
2. **无参 GET 全量打一遍**(1 发/端点,间隔 0.25–1s),把 `路径 | HTTP|大小 | 响应体前 120 字` 落 TSV
3. **按响应体签名分类**(比按状态码分类准):

| 类别 | 响应特征 | 含义 |
|---|---|---|
| `LOGINF` | 统一的 `登录状态已失效` 信封 | 被过滤器拦,非白名单 |
| `SYSERR` | `code:500 系统异常` / `参数错误` / `xx不能为空` | **已过过滤器**,进了控制器,只是缺参数 ⇒ 白名单 |
| `OTHER` | 真实数据 / `code:0` | 白名单且有数据 |
| `404` | `{"path":"/error","code":-100102,...}` 之类 | 路径不存在 |

4. **只有 `OTHER` 才要带走全量 body**;`SYSERR` 值得留档(它们是"过了鉴权还没吃参数"的候选)
5. **补一发无 cookie 复harvest** 证明未授权(带 cookie 抓到的东西在报告里说服力弱一档)

**别漏的错误码分层**:同一站上 `2048`/`20010`/`-1001`/`-1002`/`-200` 可能分别是
"登录失效 / 登录失败 / 用户态不可用 / **被限流** / 通用未登录"。看到 `-100102 请求过于频繁` = 限流,**立刻停手冷却**,
不要当成漏洞或"目标封我"。

## 3. 第二套面:移动端 H5 / APP 包(分开挖,常更松)

PC 端白名单紧,不代表 APP 端紧。找到移动端入口就单独挖一遍:

```bash
for p in /phone/ /h5/ /m/ /wap/ /app/; do curl -s -o /dev/null -w "%{http_code} $p\n" "https://T$p"; done
```

- 本次 `/phone/` 是 **CRA 打包**(`/phone/static/js/main.<hash>.chunk.js`),与 PC 的 umi 完全两套
- 从 main chunk 提端点:`grep -oE '"/(user|brand|goods|aweme|monitor|sysUser)/[A-Za-z0-9_/]{2,40}"'` → **174 条**
- **有/无 cookie 各扫一遍**(§2 的分类法),本次从中新挖出 PC 面没有的未授权端点:
  `/common/dyCid`(**1.16 MB 完整类目树**,比 PC 的 `/common/allCid` 大 5 倍)、
  `/common/mobile`(APP 配置:版本号/更新日志/类目映射,还顺带泄出另一条产品线名)、`/common/festivalList`
- 同时带 cookie 的那一遍用来找**功能面**(如 `/user/detailInfo`、`/user/api/unlock`、`/sysUser/purchase/list`)——
  它们多半卡权益,但接口名与参数结构是后续判断的输入

## 4. UMI/webpack 异步 chunk 的两个坑(定位页面级参数/字段名时)

1. **chunk URL 规则**:`<id>.<hash>.async.js`,hash 来自 runtime 里的一张 **id→hash 映射表**
2. **同一个 bundle 里可能有多张同形映射表**(JS 一张、CSS 一张)。用错表 → 每个 chunk 都返回
   ~477 B 的 `NoSuchKey` 错误页。**选表判据:已知可用的一对必须对得上**
   (例:`36 -> b1af90f8` 能下到 1.5 MB 真文件)。做法:提取所有映射块,挑包含该已知配对的块
3. 路由 → chunk:`{path:"/deck/anchor_analysis",component:...Promise.all([n.e(0),n.e(8),...])}`
   → 下这几个 id 的 chunk → 在页面 chunk 里搜目标端点名,前后各 300–600 字就能拿到**真实参数名与字段名**
   (本次由此确认了 `contactWay` 过滤键与前端 `vipLevel===2` 的硬拦截文案)

## 5. 纪律

- 全量枚举 = 每个端点 1 发;别对单个端点反复试参(既慢又容易触发限流)
- 低频、串行;命中限流码立即停,冷却后再继续
- 枚举结果(TSV)留着 —— 它是后续所有判断的索引,也是报告附录的证据
