# 摸自研接口的形状:空体探针 + 回显 oracle(附一条 opsec 红线)

补充 `write-opsec-and-api-shape-discovery.md` §二(该文已被 curator 读写守卫锁住,无法就地改,以此处为准)。

二开低代码后台会新增大量自定义接口(设备管理 / 构建链 / 代理节点 / AI 工作流…)。
**别猜参数名、别急着翻前端 JS** —— 用**空体 / 错类型**让框架自己把接口签名吐出来。
实测(2026-09,GVA 二开站)补上三种该文没写的报错形态:

| 报错 | 含义 / 下一步 |
|---|---|
| `json: cannot unmarshal object into Go value of type []xxx.Yyy` | **body 要的是 JSON 数组,不是对象** ⇒ 把 `{}` 换成 `[{...}]` 再打。类型本身即接口签名,连字段名都不用猜 |
| `不支持的会话类型` / `保存会话失败` / `获取会话详情失败` | 自定义校验 / **枚举值域未知**:保持字段名**换值**试(`sessionType` 之类);报错说法变了 = 字段名已对 |
| 错误响应里带 `data.filePath` 之类的**回显** | 接口把**它实际要用的路径**回显出来了 ⇒ 内部拼装规则与落点当场暴露 |

## 回显型 oracle 是性价比最高的一档

典型:`POST /fileUploadAndDownload/breakpointContinueFinish` 无论传 JSON 还是 form,都回

```json
{"code":7,"data":{"filePath":"./fileDir/"},"msg":"文件创建失败"}
```

这个 `filePath` = **固定基址 + 数据库记录里的 `file_name`**(记录为空 ⇒ 拼出空文件名 ⇒ 失败)。
一次调用就暴露了“**落点由库里的字段决定,不由请求参数决定**”,直接省掉整轮参数名爆破。

⇒ 见到这类回显就顺着它反推内部拼装,**别继续猜参数名**。

## ⚠️ opsec 红线:空体探针只能打在“读 / 校验型”接口上

对**写型**接口 —— `system/setSystemConfig`、`autoCode/createTemp`、`installPlugin`,
以及任何 `create* / save* / update* / delete*` —— **绝不要发 `{}`**。

它们可能“校验通过 → 拿空值去写配置 / 落文件”,把对方配置**写成空的(不可逆)**。

正确做法:写型接口用**从读接口回读的完整原值做 round-trip**,只改目标的那一个字段,
发完**立刻回读验证**(并记好原值以便还原)。例:

```
GET  /system/getSystemConfig            → 完整 config(原值存盘)
POST /system/setSystemConfig {config: <原值,仅改 1 个字段>}
GET  /system/getSystemConfig            → 回读确认只动了那一个字段
```

本条来自一次**刻意把这些接口排除在探针集之外**的判断 ——
省下的不是一次请求,是整站的可用性。
