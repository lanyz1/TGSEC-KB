# 机队实体台账与续费取证

用途:用户要"服务器信息 / 续费"时,把主控 + 跳板 + 采集机的实体身份取全,产出可被控制台检索的清单(不含凭据)。表内数字取自最近一次实登快照,**续费前重跑刷新,别照抄旧表**。

## 取证命令(经主控跳转,凭据不出主控机)

```bash
# 主控自身
ssh -p 12971 root@128.241.245.73 'hostname; nproc; free -m | sed -n 2p; df -h / | tail -1; \
  uptime -s; lsb_release -ds; tail -3 /etc/resolv.conf'

# 逐台采集机(SSH 已 publickey-only ⇒ 用主控私钥)
ssh -i /root/.ssh/id_ed25519 root@<采集机IP> 'nproc; free -m | sed -n 2p; df -h / | tail -1; uptime -s; \
  curl -s http://100.100.100.200/latest/meta-data/instance-id; echo; \
  curl -s http://100.100.100.200/latest/meta-data/instance-type; echo; \
  curl -s http://100.100.100.200/latest/meta-data/region-id'

# 断供横比(在主控上跑;落后最多的一台就是已断供机,其时刻=断供起点)
for d in /data_raw/*/; do echo "$(stat -c %y "$d" | cut -d. -f1)  $d"; done | sort
```

- 采集机清单与现行口令源 = 主控 `/opt/v6/jumpers.json`;**桌面凭据单可能已过期**,直连失败先分认证类:`BadAuthenticationType` = 服务端已禁口令(换密钥),`AuthenticationException` = 口令错,超时/丢包 = 真失联。
- 失联机身份:阿里云 hostname `iZ<instance-id>Z` ⇒ 去掉首 `iZ` 与末 `Z` 即实例 ID,ping 不通也能让用户按 ID 搜到实例。
- 跳板池 7 台(渗透用)凭据与在线状态见 skill `ip-ban-bypass` 的 `references/jump-pool-live-*.md`。

## 主控(95306 主服)

| 项 | 值 |
|---|---|
| 公网/登录 | `128.241.245.73:12971`(root + 密钥);主机名 `jnjjn` |
| 归属 | 美国 San Jose;AS213802 Tianfeng (Hong Kong) Communications Ltd;上行 NTT America(**非阿里云/腾讯云**) |
| 规格/系统 | 8 vCPU / 8 GB / 238.5 GB 盘;Ubuntu 22.04.3;时钟 UTC |
| 续费线索 | `/etc/resolv.conf` 残留安装串 `toplink os installer` ⇒ 经销商面板按 IP 找订单;月付则到期≈开机日+30 天 |
| 承载 | `/opt/v6`(代码+日志+crontab 12 条)、`/data_pool`、`/data_raw`、merger / bot / orch8b |
| 约束 | 机内无 AKSK/RAM 角色 ⇒ 到期日读不到;**续费即可别重建**,迁移要整搬 `/opt/v6` + `/data_pool` + `/data_raw` + crontab |

## 采集机 12 台(全 `ecs.e-c1m2.large` 2C4G/49G,阿里云 ECS)

`sh0` 沪 `8.133.188.178` cn-shanghai `i-uf67iymaan2xa5ol7zbg`｜`sh1` 杭 `121.43.97.73` cn-hangzhou `i-bp1113ro087u3soq9gjc`(hostname 反推)｜`sh2` 穗 `8.138.236.124` cn-guangzhou `i-7xv1zde7cxgtpmcjgwb3`｜`sh3` 蓉 `47.108.152.60` cn-chengdu `i-2vc9y5tbpj298oplp3lq`｜`sh4` 沪2 `8.133.212.134` cn-shanghai `i-uf6irfmo6asik678bhfr`｜`sh5` 蓉2 `47.108.173.230` cn-chengdu `i-2vc3dzk5aunevnce7gmq`｜`sh6` 青 `47.104.139.212` cn-qingdao `i-m5e9h0a1iicizpqiw6mm`｜`sh7` 深 `47.107.124.62` cn-shenzhen `i-wz9bgkg8790guzgp4mm5`｜`sh8` 沪3 `47.103.86.92` cn-shanghai `i-uf6f3uhx4lhjl2x75c45`｜`sh9` 汉 `8.148.7.168` cn-wuhan-lr `i-n4a4rl5bawefv3bma94g`｜`sh10` 蒙 `8.130.171.221` cn-wulanchabu `i-0jlid88hszgddl82991k`｜`sh11` 源 `47.120.9.89` cn-heyuan `i-f8zeqjmd6xtvdn34z3pt`

开机日(月付 = 账单周年参考):08-29 `sh2`/`sh3`;09-01 `sh4`–`sh7`;09-08 `sh0`;09-09 `sh8`–`sh11`。

## 渗透跳板池 7 台(非采集管线,勿与采集机混为一谈)

阿里云 5 台(均 2C4G/49G,同批开机):`8.133.234.161` cn-shanghai `i-uf6cwlks9mmqoaqwsy0a`｜`120.76.176.155` cn-shenzhen `i-wz96gdykr9rls3ml4rs3`｜`101.200.225.184` cn-beijing `i-2ze0ulwyugv821t3b4j5`｜`116.62.103.69` cn-hangzhou `i-bp15n9qjd7f9c4pv31dm`｜`47.108.106.137` cn-chengdu `i-2vccvynnamew6xa4b8k3`;电信 IDC 2 台:绍兴 `124.248.67.181:22`(2C4G/49G)、宁波 `110.42.103.114:56102`(**4C**/3.9G/39G)。
已停/不可达(不续):深圳电信 `103.109.21.198`、内蒙古 `43.240.221.227`、历史 `8.130.150.18`、曼谷腾讯 `43.152.240.239`;RDP 跳板 `153.120.128.180:3389`(仅端口通)。

## 交付骨架(用户说"续费"时的清单结构)

```
# 95306 项目 · 服务器续费清单
> 取证时间 + 取证方式(实登只读)+ 本文件不含凭据
一、主控(最关键,先确认到期)         二、跳板机(7 台表:IP:端口 / 实例ID / 地域 / 规格 / 开机 / 状态)
三、‼️ 比续费更急:断供机(断供起点 / 漏采窗口 / 分片 / 实例ID / 恢复动作)
四、采集机 12 台表 + 续费节奏         五、去哪续(阿里云控制台按 IP 或实例ID 搜;经销商面板按 IP 找订单)
六、为什么机器上报不出到期日(无 AKSK/RAM)  七、凭据(不在本文档内,只写"存在哪里")
```

落盘 `D:\渗透\95306_服务器续费_<日期>\` + 桌面一份;聊天回三条结论 + `MEDIA:` 该文件。**查不到的一律如实写"读不到",不编到期日**;文档内不写任何口令/私钥。
