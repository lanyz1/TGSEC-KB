## 1. 服务器侦察(先做)

paramiko SSH → 查 OS/CPU/内存/磁盘/已装软件(PHP/Apache/Nginx/宝塔)/防火墙/监听端口。
CentOS7 最小化典型状态: 无 firewalld(iptables ACCEPT 无过滤), rpcbind(111 公网可达, 停)、postfix(25 仅本机, 可停)、sshd 非标端口。

