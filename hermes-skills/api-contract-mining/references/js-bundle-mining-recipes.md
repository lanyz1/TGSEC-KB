# 单包挖掘配方（实测有效）

目标：从一个几 MB 的压缩 JS 单包里，挖出「真路径 / 真方法 / 真字段 / 权限表 / 配置键 / 危险渲染」。

## 0) 先建索引
- 保存为 `loot/<hash>.js`，记住**构建哈希文件名**（每次部署变，写进报告便于复现）
- 行数极少但字符数极大 → 是打包产物，**不要按行处理**，一切按字符偏移切片

## 1) 关键字上下文窗口（grep）
```bash
grep -o '.\{170\}"transfer".\{300\}' loot/index-XXXX.js | head -3
grep -o '.\{120\}red-packets.\{260\}' loot/index-XXXX.js | head -5
```
- `.{N}str.{M}` 前后各留 N/M 字符，足以看清「调用点 + 传参」
- ⚠️ **正则里的 `]` 会截断模式**（如 `HZe=[...]` 想只匹配 `]` 前的数组）→ 别用 grep 抽数组，改用 Python 切片

## 2) 数组 / 枚举 / 白名单（Python 切片，别用 grep）
```python
js = open("loot/index-XXXX.js", encoding="utf-8", errors="replace").read()
i = js.find("HZe=[")          # 或 "stepUp"、"mfa_enabled"、权限数组名
i = js.find("[", i)           # 找到数组起点
print(js[i:i+1600])           # 直接看原文，人工读
```
- 二次确认(step-up)白名单通常是**路径正则数组**，数组长度即覆盖面 → 与端点清单做差集找缺口
- 权限/角色/菜单表：正则 `\{value:"([a-z0-9_-]+)",label:"([^"]+)",path:"([^"]*)"`  
  能一次拿到「权限键 + 中文标签 + 前端路由」，直接算出权限模块总数与角色名

## 3) 真字段：先找定义，再找调用点
- 打包器把 API 包装函数定义为 `function da(e,t){...}`，调用点长成 `da("/api/v1/xxx",{method:"POST",body:JSON.stringify({...})})`
- **找调用点要排除定义点**（否则第一个命中是自己的定义）：
```python
for m in re.finditer(re.escape("Bkt("), js):
    print(js[m.start()-120:m.start()+420], "\n---")
```
- 表单类字段最好从**中文标签**反查：搜 `转账` / `红包` / `收款` → 从命中位置 ±400 字符读出 `onFinish` 的对象字面量
  - 实测收益：`to` → 真名 `recipient`；`/transfers` → 真路径 `/transfer`；`/red-packets/create` → 真路径 `/red-packets`

## 4) 配置键金矿（带中文标签）
```python
re.findall(r'"([a-z0-9_]*(?:withdraw|deposit|exchange|transfer|finance|fee|limit|min|max|threshold|totp|mfa|2fa)[a-z0-9_]*)"\s*:\s*\{\s*label:\s*"([^"]+)"', js)
```
- 一次拿到全量配置键 + 中文说明 → 业务通道 / 费率 / 风控阈值 / 币种白名单全暴露
- 同族键（`*_cny_*`）可判定**法币通道是否存在**；`*_auto_threshold` 透露自动审核阈值；能量/资源类键（`usdtSweepRequiredEnergy`）揭示链上归集成本模型

## 5) 危险渲染 / 前端 XSS 可行性
```python
for k in ["dangerouslySetInnerHTML", "insertAdjacentHTML", "document.write", "eval(", "innerHTML"]:
    print(k, js.count(k))
```
- `dangerouslySetInnerHTML` 只出现在 React 运行时（property setter / 组件系统）→ **应用代码零使用** → 存储型 XSS 判死
- 同时看 CDN/静态域响应头：缺 `X-Content-Type-Options` / CSP 记一笔（但若上传侧强制重命名 + 强制 content-type + 服务端验图，则不可利用）

## 6) i18n 文案 = 服务端错误语义字典
- 打包包里的文案函数（`he("key")` / `t("key")`）与映射表含**全部 UI 文案**，包括服务端返回的错误串与状态枚举（`pending_fund_review` 之类）
- 用途：提前知道每个闸门会返回什么文案 → 探测时用文案差异判定「过了哪一关」

## 7) 管理端 / 小程序双应用识别
- 搜 `管理后台`、`admin`、`login`、`X-Admin`、`csrf` → 若同包内存在，**管理端前端完全到手**：登录协议、CSRF 取值、step-up 弹窗、角色枚举、每页快捷动作
- 登录协议要素：`baseURL`、登录路径、CSRF cookie 名与取值来源（是否 httpOnly）、step-up 头名（`X-Admin-Password` / `X-Admin-MFA-Code`）、失败分支文案
- 硬编码凭据扫描：搜 `password`、`secret`、`token`、`apiKey` 的字面量赋值；**通常是零**，别据此编故事
