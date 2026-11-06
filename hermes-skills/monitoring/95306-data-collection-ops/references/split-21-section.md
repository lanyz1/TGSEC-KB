## 机队实体台账 / 续费取证(用户说"续费"时)

用户说"把主控和跳板机的服务器信息整理一下 / 我要续费"时按此走:

1. **先对上身份再取证**:"跳板机"在本项目是混用词——可能指 ①渗透跳板池 7 台(凭据见 skill `ip-ban-bypass`)②12 台采集机 ③**主控本体**。**主控 = `128.241.245.73:12971`(hostname `jnjjn`,US San Jose,AS213802 Tianfeng)**,管线里主控↔采集机直连、**无独立跳板**;交付前用 IP 逐条对齐,别把主控写成"跳板机"(踩过)。
2. **逐台实登只读取规格**:`nproc`/`free -m`/`df -h`/`lsb_release`/`uptime -s`/`/proc/net/dev` + 云元数据 `curl -s http://100.100.100.200/latest/meta-data/{instance-id,instance-type,region-id,zone-id}`。采集机 SSH 已 publickey-only ⇒ 用主控 `/root/.ssh/id_ed25519`;12 台清单与现行口令源是 `/opt/v6/jumpers.json`(桌面凭据单可能已过期)。
3. **到期日读不到的如实说**:机内无 AKSK/RAM 角色 ⇒ 取不到 `ExpiredTime`;交付口径 = **`uptime -s` 开机时刻当账单周年** + **云实例 ID 交出去供控制台检索** + "去哪续",不要编到期日。
4. **失联机也要给可检索身份**:阿里云 hostname 反推实例 ID、元数据取法、"到期停机"定性见 skill `monitoring-pipeline-ops`「机队实体台账、断供与到期诊断」。
5. **断供与否按 `/data_raw/<机名>/` 最新 mtime 横比**:某台明显落后其余台 = 已断供,该时刻即断供起点 ⇒ 报出**漏采窗口**与该机分片覆盖面(`md5(proj)%12`),它是"比续费更急"的事项。
6. **交付**:`D:\渗透\95306_服务器续费_<日期>\*.md` + 桌面一份,结构 = 主控卡 / 跳板池表 / 急事(断供机) / 采集机附录 / 去哪续 / 为什么读不到到期日;聊天里给三条结论 + `MEDIA:` 本文件;**凭据一律不写入清单**。台账快照与刷新配方见 `references/fleet-inventory-and-renewal.md`。

