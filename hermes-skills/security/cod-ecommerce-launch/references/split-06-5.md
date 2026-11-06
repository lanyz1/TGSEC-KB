## 5. 数据迁移(地区库/大表)

- 从线上 API 抓全量: 逐层 BFS + ThreadPoolExecutor(8) + **每层即时 commit + flush 输出**(别在最后才 commit, 中断全丢)。
- **大坑: BFS 会把末级节点也当父级再发请求**(tw711 7474 个门市 × 2s/请求 ≈ 30 分钟空转)。必须**深度限制**: queue 存 (pid, depth), depth >= max_depth 只记录数据不再请求子级。门市/末级树按 code 设 max_depth=2~3。
- 跨库合并: 上传本地库到 /root/local.db → 服务器 PHP `ATTACH` + `INSERT OR IGNORE INTO dst SELECT ... FROM src`(**不要整库覆盖**, 保留服务器订单/设置)。**ATTACH 必须在目标连接上执行**(`$dst->exec("ATTACH '/root/local.db' AS src")`, 再 `$dst->exec("INSERT ... FROM src.dr_linkage")`)—— attach 到源连接会报 `no such table: src.dr_linkage`。注意 exec_command 直接传 PHP heredoc 可能无输出(EXIT 255), 把脚本写成文件上传再执行更稳。

