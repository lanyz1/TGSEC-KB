# 自愈型 SOCKS5 隧道:`scripts/robust_socks.py`

本 skill 的 `scripts/jump_socks.py` 是**单连接**实现,够用于"发几发请求看看出口通不通"。
一旦进入**长时间作战**(几小时的渗透会话),它会成为瓶颈甚至直接掉线。本文记录替换件与踩过的坑。

## 什么时候换用 robust_socks.py

`scripts/robust_socks.py` 与本 skill 同级目录,用法相同:

```bash
python scripts/robust_socks.py <jump_ip> <port> <user> <pass> <local_port>
# 后台常驻:terminal(background=true)
# 之后 requests 用 {"http":"socks5h://127.0.0.1:<local_port>", "https": 同}
```

相比 `jump_socks.py` 的改进:

- **多连接并发**:每个客户端连接独立处理(单连接实现下,一个 keep-alive 会话会占死隧道,
  后续请求全部 `Connection closed unexpectedly` —— 这是个非常像"目标挂了"的假象)
- **SSH 掉线自动重连**:本地监听端口**永不关闭**,底层 paramiko transport 断了就重连
- **监听常驻**:本地端口一直 LISTENING,便于随时判断"是隧道没了还是目标没了"

## 坑 1:隧道会静默死掉,而症状看起来像目标故障

单连接隧道跑一段时间后,症状是 `socks.GeneralProxyError: Socket error: Connection closed unexpectedly`
或 `ProxyConnectionError: ... actively refused`。**先怀疑隧道,再怀疑目标。**

判别:

```bash
netstat -ano | grep "127.0.0.1:<local_port>"     # 还有 LISTENING 吗
```

- 端口没了 → 隧道进程死了,重启即可
- 端口在但一直 TIME_WAIT / 连不上 → 上游 SSH 断了(单连接实现的典型),换 robust 版
- 端口在、连通正常 → 才去查目标

## 坑 2:后台进程可能被环境回收,长任务要能自愈

实战中隧道后台进程在**约 17 分钟**后被回收(termination_source: process.kill),
一直以为"网络不稳"。对策:

- 用自愈版(本地监听常驻 + 自动重连),进程被回收后**重启进程即可恢复**
- **不要把关键状态放在隧道进程里**;每轮把结果落盘,随时可续
- 周期性 `netstat` 自检,别等请求全失败才发现

## 坑 3:不要为了重开隧道去 kill 已有进程

用户铁律:**kill/重启任何运行中进程前必须先获同意**。隧道端口被占/上游坏了时,正确做法是
**换一个新本地端口起第二条**,而不是杀掉旧进程。旧进程自然退出后再清理。

## 坑 4:先确认"免票请求"和"带票请求"走的是不是同一条隧道

多连接实现下,裸 `requests.get(...)`(自己新建连接)与会话 `session.get(...)`(复用连接池)
行为可能不同。做鉴权对比测试(要摘掉 token 头)时,**用同一个会话对象、只摘 header**,
不要另起一个裸 requests 会话 —— 否则会把"隧道连接问题"误判成"该接口需要鉴权"。
