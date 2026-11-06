## 11. 配置类接口的 POST 覆盖坑

- **`isset($_POST['key'])` 就覆盖已存配置的接口, 测试时传占位符会把真配置破坏**(实测: tg_getupdates 传 `bot_token=USE_SAVED` 把真 token 覆盖, 后续全部 404)。测试这类接口要么传真值, 要么设计成"空则不覆盖"。类似地, tg_save 类接口保存前先 `array_merge(tg_config(), $c)` 防字段缺失清空。

