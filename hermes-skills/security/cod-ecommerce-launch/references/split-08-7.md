## 7. 上线收尾清单

- [ ] 清测试数据: dr_order/dr_weblog/dr_fb_event/dr_cloak_log/dr_cloak_visit/dr_blacklist(保留 dr_pro/dr_linkage/dr_settings); 清完用 COUNT(*) 逐表验证=0
- [ ] 斗篷总开关默认关闭; 推荐配置写进运维文档(回流页 URL 必须填, 否则命中显示白页)
- [ ] **回流页文件必须真实存在**(back.html 等): 斗篷命中 JS 跳转, 文件缺失 = 404 白屏(隐蔽坑, 上线核查必测 `curl -k -o /dev/null -w '%{http_code}' https://域名/back.html`)
- [ ] 像素实测: debug_token 200 + events 端点 `events_received:1`(token 有效性最终证明, 不是"保存成功")
- [ ] SQLite 每日备份 cron: `sqlite3 db ".backup '...'"` 或 cp, 保留 7 天
- [ ] 停 rpcbind/postfix; 装 fail2ban(sshd 非标端口 jail + http-get-dos); 核查 `ss -tlnp` 只剩 80/443/SSH
- [ ] 运维手册(账号/备份恢复/代码更新流程)上传 /root/
- [ ] 生产回归: HTTPS 端到端下单(登录态 + CSRF)且后台能搜到订单

