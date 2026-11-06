## 8. 测试/验证坑(curl / shell)

- **URL 带 `&` 必须整体加引号**, 否则 shell 拆成后台任务 → 保存 API 静默失败(斗篷"没开"假象, 排查半天)
- Windows 原生 curl 写 `/dev/null` 失败(exit 23)→ 用 `-o NUL`
- cookie jar 域名匹配: 请求 `127.0.0.1` + Host 头时, jar 里以域名为域(如 xeelee.top)的 cookie **不会发送** → 测试手动 `-H 'Cookie: name=value'`
- HTTPS 站点测试: 必须 `curl -k https://...` + Host 头; http 会 301
- **验证"登录成功"看 302 Location 或业务内容, 200 不等于成功**(登录页也是 200!)
- Python `-c` 多层引号易炸 → 写脚本文件; paramiko exec_command 传复杂 heredoc 可能丢输出 → 先 write_file 上传再执行
- 本地与服务器的 cfg() 实现可能不一致(本地支持无参返回全量, 服务器必须带 key)——传配置数组到模板时逐键 cfg('key') 显式取, 别用 cfg()
- PDO execute 的数组必须从 0 连续索引: array_unique/array_filter 会保留原键, 导致 `bind or column index out of range`(500), 加 array_values() 重排
- 长抓取/安装放后台跑(notify_on_complete), 别占前台超时(用户会中断)
- **PHP PDO 绑定坑: `array_unique(array_filter(array_column(...)))` 返回非连续键数组, PDO execute 按键索引绑定 → `SQLSTATE[HY000] column index out of range`(500 无输出)。任何要传给 execute() 的数组一律 `array_values()` 重排**(区域管理父级 IN 查询实战)

