# 365jz Checkquery WAF — 全解 (实测 2026-09, PHP 8.1.31 / MySQL 5.7.44)

源码: `source/class/jzmysql.class.php`(Checkquery;query/update 在 `$this->safeCheck` 为真时调用)。

## 处理管线
1. **引号剥离**: 每个引号串替换成字面 `$s$` 存进 `$clean`。内层扫描配对 `'` 与 `\`:下一个引号 pos1 vs 下一个反斜杠 pos2;pos2 < pos1 → 跳过该对(`pos=pos2+1`);否则在 pos1 闭合。
2. `$clean2 = strtolower(preg_replace('~\s+~s', ' ', trim($clean)))`。
3. 规则(观察到的顺序):
   - `@` | `char(` | `"` | `$s$$s$` → 拒("unusual")
   - `\bunion\b` | `\bsleep\b` | `\bbenchmark\b` | `\bload_file\b` | `\boutfile\b` → 拒
   - 注释检测: `#`、`--`、`/*` → 拒
   - **子查询: `preg_match('~\([^)]*?select~s', $clean2)` → 拒**。即任何 `(` 之后"到 select 之前"不含 `)`——覆盖所有 `(select` 形态(小写化+空白压缩后)。
4. 拦截输出页(~226–288B): `sql：<完整SQL>; Safe Notes: Request Error!`
5. `safeCheck`: jzmysql 构造函数设 TRUE;**只有 `zzadmin/config.php`(约13行)设 FALSE** → 后台侧全部 DB 调用不过滤。

## 已验证放行
- `extractvalue(1,concat(0x7e,EXPR))`、`updatexml(1,concat(0x7e,EXPR),1)` → 报错读(XPATH 报错文本)。
- hex `0x...`、`if()`、`case`、`concat`、比较、`and`/`or`。
- `dumpfile` 不在词黑名单(但 INTO DUMPFILE 只在语句尾合法,注入点通常够不到;`;` 堆叠同样死,见下)。
- EXPR 内不得含 `(select`(硬过滤),也不得含 `@`、`char(`、`"`。

## 长度布尔 vs IF+extractvalue（2026-09-22）
- **可用**: `id=-1 or (ascii(substr(user(),N,1))=X)` 比响应体长（真大/假小）。
- **坑**: `if(cond, extractvalue(1,concat(0x7e,1)), 0)` 在目标 5.7 上常 **cond 真假都 XPATH**（优化/两边求值）→ 不能当布尔。
- 子查询绕过复测仍死: `/**/`、换行、`%0a`、`/*!*/`、`json_array((select…))`、`SeLeCt` 等 → 一律 Safe Notes / sub select detect。

## INTO DUMPFILE 实战结论
- 词法放行 ≠ 可利用: WHERE 子句尾 `into dumpfile` → 1064；UPDATE…`into dumpfile` → 1064。
- 库账号常见 `GRANT USAGE ON *.*` + `ALL ON db.*` → **无 FILE**，即使改成合法 `SELECT 'x' INTO DUMPFILE` 也 denied。
- 先 `SHOW GRANTS` / 实验室 dumpfile，无 FILE 立刻停，别在 tid 上盲试路径。

## 已排除向量(实测;没有新信息别重跑)
- **PCRE 回溯炸弹**: 设想嵌套 `(((((` + `(select` 逼爆 `pcre.backtrack_limit` 实现 fail-open。实测(实验室,PHP 8.1.31): 2000+ 层嵌套 preg_match 立即返回 0/1,不触发 backtrack-limit 错误——现代 PCRE 对懒惰扫描做了优化。死。
- **`;` 堆叠**: mysqli::query 单语句;`SELECT 1; SELECT 2` → 第二段语法错,无副作用执行。代码库从不用 multi_query。死。
- **反斜杠/引号剥离差异**(k=1..6 反斜杠矩阵): 能过检查器的形态全部 MySQL 语法错——合法 SQL 里 `((` 与 `select` 之间只能是空白/注释,构造不出"检查器可见 `)` / MySQL 不可见"的分歧。死。
- **%25 双编码**(`%2573elect`): 过检查器(字面 `%73elect` 不含 select),但 MySQL 收到同一字面 → 语法错。两层读同一份解码后的字符串,无分歧。死。
- **时间盲**: `sleep`/`benchmark` 词拦;`@` 拦(无用户变量)。死。
- **sitemap.xml?action=**: 静态文件服务,参数被忽略。
- **install/ 重装**: 只剩 `install.lock`(返回 `ok`);安装器 PHP 已清("File not found.")。
- **直连 3306 / 服务器间**: ACL 对攻击机 IP 与同族服务器 IP 都回 `Host '...' is not allowed` —— 仅 localhost。死。
- **888 端口**: Apache 对全部 Host/路径 403(死预览口)。
- **FTP**: Pure-FTPd,禁匿名;PASS 阶段 `421 Unable to read the indexed puredb file`(服务器虚拟用户库损坏);11 用户×12 密码矩阵灭。
- **admin7799 精选喷洒**: ~5400 候选耗尽未中(含复用/特征表;用户反对纯字典,只有拿到真正新词表再考虑)。
