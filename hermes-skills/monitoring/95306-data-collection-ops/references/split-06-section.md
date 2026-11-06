## 采集端改动与验证纪律（每次改采集端/名单必走）

- **双侧核验，缺一不可**：①主控 `md5sum master/bk_worker.py` == 采集机 `md5sum /tmp/bk_worker.py`；
  ②采集机 `grep -c <新符号> /tmp/bk_worker.py` 命中；③采集机 `grep -o '<新字段>.\{0,20\}' /tmp/bk8_bf_ctx.json` 看到新名单。
  只核验主控侧会漏掉「代码/名单还没真下发」，生产照旧跑旧文件。
- 采集机上的探针**必须 `importlib` 显式加载 `/tmp/bk_worker.py`**（生产真身）；
  裸 `import master.bk_worker` 会落到 `/opt/v6/current` 旧树 ⇒ 新字段恒空、误判“未生效”。
- `rail_rows()` 返回 **`(rows, fail)` 元组**，先解包；直接迭代报 `'list' object has no attribute 'get'`。
- 只读探针免同意；**改采集端代码 / 重启 / 杀进程必先告知并获同意**。改动一律留 `.bak_<ts>_<name>` + 一行回滚命令，静默不发公告。
- 哨兵/轮询：按**行号锚定**（`N+1` 起算，别用 `tail -n +$N`——会把末行算进新窗）；
  ssh 超时/空输出**绝不当作完成**；链路抖动重试，不中断整条取证链。

