# 多列写入的真相 + 权限缓存(两条实测修正)

本文件修正 SKILL.md 铁律 #5「单列限制」与 `gva-export-template-sqli-write.md` §3 的结论。
**那两条把"我自己的 bug"写成了"目标的限制"**,会把后续会话引离唯一可行的复刻账号路线。

## 一、"多列不写库"是我的 xlsx 生成器 bug,不是目标限制

**现象**:单列模板写库成功;2 列/3 列模板一律 `record not found`,不写库。
看起来像"通道只支持单列"。

**真因**:我手写的 xlsx 生成器每行只 emit 第一个单元格:

```python
# 错的
body = "".join('<row><c t="inlineStr"><is><t>%s</t></is></c></row>' % str(r[0]) for r in rows)
#                                                                          ^^^^^^ 只取 r[0]
```

3 列的 sheet 生成出来实际只有 1 列 —— 于是**所有多列模板都退化成单列**。

**修好后立刻成功**:11 列一次插进去(`app.sys_users` 完整行:
`username/password/nickname/header_img/authority_id/enable/created_at/...`),
响应 `code:0 导入成功`,**且行数从 174 → 175 真的落库**。

### 铁律:怀疑目标之前,先读回自己的产物

```python
import io, openpyxl
ws = openpyxl.load_workbook(io.BytesIO(payload)).active
print(ws.max_row, ws.max_column)          # 列数对不对?
print(list(ws.iter_rows(values_only=True)))  # 值都在?
```

**误判成"目标只支持单列"的代价**:直接放弃"复刻一个字段齐全的超管账号"这条路线 ——
而它其实是可行的。**写库失败时,先量自己的包。**

### 失败签名速查

| 报错 | 含义 | 是不是你的锅 |
|---|---|---|
| `Field 'X' doesn't have a default value` | X 列没进 INSERT | **先查你是不是没造那一列** |
| `Unknown column 'X' in 'field list'` | 列名在该版本不存在 | 二开改过表结构,换列名 |
| `record not found` | 子查询返回 NULL / 载荷超长 | 先砍载荷长度,再怀疑通道 |
| `json: cannot unmarshal number into ... type string` | 元数据的值必须是字符串 | `"888"` 不是 `888` |

## 二、写入的三层映射(完整版)

实测拼接形状:**`INSERT INTO <tableName> (\`列1\`,\`列2\`) VALUES (?,?)`**

```
表名   ← tableName 字段                完全可控
列名   ← templateInfo 的 KEY           完全可控(= 目标真实列名)
值     ← 上传 xlsx 的数据单元格(row 2 起;**第 1 行是表头**)
```

- **xlsx 表头必须匹配 templateInfo 的 VALUE(标签)**,不是列名本身。
  最少验证过的可用组合:`templateInfo={"ptype":"P"}` + 表头第一格 `"P"` + 数据格 `"<值>"`。
- **占位符个数必须与模板一致**:`sql: expected 0 arguments, got 1` = 你多/少了 `?`。
  ⚠️ **用 `-- ` 把应用追加的尾巴注释掉会导致占位符数量对不上** ——
  正确做法是让你的 `tableName` 与它追加的 `(列) VALUES (?)` **拼成一个合法语句**,而不是吃掉它。
- 想摸清形状就用语法错误当探针:
  `tableName = "... VALUES (1,2) ZZZZ"` → 报错吐出 `ZZZZ (\`列\`) VALUES (?)`。

## 三、casbin 权限:插进库里也不生效(启动时加载进内存)

想给自己补权限时,`app.casbin_rule` 格式明文可读:

```
ptype='p'   v0=<authorityId>   v1=<路径>   v2=<方法>
```

**实测**:照格式插入 4 条上传权限 + 3 条 `/*` 通配,**共 7 条**,
目标接口**依然回 `权限不足`**;探测 `freshCasbin` / `reload` / `casbin/*` 等重载路由**全部 404**。

⇒ **GVA 系把策略在进程启动时 load 进内存,DB 改动要等进程重启才认。**
**别把"用注入给自己发权限"当既定路线** —— 要么打**既有权限**的接口(优先),
要么等一次重启窗口。想确认自己有没有权限,读 `casbin_rule` 里既有角色规则,
比造账号/发权限省事。

## 四、登录成功与否常由"角色"决定,不由密码决定

同一张 `app.sys_users` 里、`enable=1`、密码也验证过的账号:

```
panghu(9100 代理管理员) → 桌面端登录成功 ✓
888 超管 / 9200 / 9528   → "用户名不存在或者密码错误" ✗
```

⇒ **入口做了角色白名单。先怀疑入口分角色,再怀疑密码** ——
否则会反复重造账号、重设密码,白烧时间。

## 五、收尾纪律:只能插不能删

本通道**没有 UPDATE/DELETE**(`;` 堆叠被禁)⇒ **插进去就清不掉**。
- 测试用最小足迹(标记行用可识别前缀,便于日后批量清)
- **如实向用户交代残留行数与内容**,不要说"已清理干净"
