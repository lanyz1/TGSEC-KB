# 服务器 522 事故排查 + 预防（2026-08-10 实录）

## 事故经过
- 用户报"服务器是不是被攻击了，全部404进不去了" + Cloudflare 522 截图（07:11 UTC）
- 实际：**非攻击**。时间线 = 06:40 某实例 recv() failed（不稳定开始）→ 07:11 源站无响应（Cloudflare 522）→ 07:23 **系统硬重启**（云厂商看护检测到无响应自动重启，`last reboot` 无 shutdown 记录）→ 恢复

## 排查顺序（"全部404/522"标准流程，先验证再下结论）
1. **外网 curl**：`curl -s -o /dev/null -w 'code:%{http_code} time:%{time_total}s' https://qavlixor.com/`（服务器本地跑，走 Cloudflare 回源路径）
2. **本机 3000**：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/`（区分 CF 问题 vs 源站问题）
3. **PM2 状态**：`pm2 list`（online/uptime/restarts——uptime 短 = 刚重启过）
4. **nginx 错误日志**：`tail -20 /var/log/nginx/error.log`——搜 `connect() failed (111)`（上游实例挂了）、`upstream prematurely closed`（实例卡顿）、`timed out`（慢请求）
5. **系统重启识别**：`last reboot | head -3` + `who -b`——**无 shutdown 记录的 reboot = 云厂商看护硬重启**（宕机检测自动拉起），不是人为重启
6. **资源**：`free -m`（swap 是否为 0——**无 swap 时内存峰值 = 系统无响应 = 522 高危**）、`uptime`（load）、`ss -s`（连接数）
7. **access log 确认 CF 请求在进来**：`tail -5 /var/log/nginx/access.log | awk '{print $1}'`——104.22.x/172.68.x/172.71.x = Cloudflare IP，200 正常

## 根因分析（本次）
- 4 个 PM2 实例各 ~1.3GB（合计 5.3GB）+ **swap = 0** + 部署时 `next build` 峰值 → 内存峰值时系统无响应 → 云厂商看护重启
- 部署 build 是前台 exec（deploy.py 等 build 完），build 期间 PM2 仍跑旧代码 + build 吃内存 → 峰值叠加

## 预防（已落地，可复用）
1. **swap 4GB**（无 swap 是内存峰值直接卡死系统的根因）：
   ```bash
   fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
   echo '/swapfile none swap sw 0 0' >> /etc/fstab   # 持久化
   ```
2. **PM2 max-memory-restart**（单实例内存泄漏自动重启，防拖垮全部）：
   ```bash
   for id in 0 1 2 3; do pm2 restart $id --max-memory-restart 1600M; done
   pm2 save   # 持久化
   ```
3. **验证**：`free -m | grep -i swap` 显示 4095；`pm2 jlist | grep max_memory_restart` = 1677721600；`curl 200`

## 通用教训
- **用户报"被攻击/全挂了"≠攻击**：先跑排查顺序 1-7（日志证据说话），再回复结论——本次全部 200 后确认是瞬时宕机已自愈
- **时间线重建法**：用户报障截图时间（07:11） vs `uptime`/`pm2 uptime`（07:23 重启） vs nginx error log 时间戳——三个时间点一拼就是完整事故链
- **522 专属含义**：Cloudflare 连不上源站（TCP 通但源站无响应/超时）——源站 curl 200 但用户 522 = 瞬时宕机已恢复 或 CF 回源配置问题（本案例是前者）
- **next build 部署时的内存峰值**是 522 诱因之一：大项目（.next-build 2GB+）build 时与 4 实例共存，无 swap 则高风险
