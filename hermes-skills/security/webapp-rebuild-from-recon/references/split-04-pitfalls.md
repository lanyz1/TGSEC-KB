## Pitfalls(实测)

- **HTML→PHP 模板转换用脚本做,转换后必须 `php -l` 验证**:
  - 子串碰撞:`tcskuData: {` 含子串 `skuData: {`,直接 `str.find` 会替换错对象 → 用正则 `(?<!tc)skuData: {` + 括号深度配对
  - 正则替换生成 PHP 代码时会产生 `$pro[\'id\']` 反斜杠残留 → 只在 `<?php ... ?>` 段内清理反斜杠,**别动 JS 里合法的 `\'` 转义**
  - 模板内嵌 PHP 变量(meta og:title 等)用 `json_encode()` 输出,注意 HTML 属性引号
- **路由命名**:`s=模块&c=控制器&m=方法` → 模块文件 `modules/{s}.php`,函数名 `{c}_{m}()`(如 c=show&m=index → `show_index()`,不是 `pro_show()`);c 缺省时 c=模块名;写错名字会"方法不存在"
- **JS 变量文件解析**:`var linkage_tw =[{...}];` 等号后可能无空格 → 正则 `var \w+\s*=\s*(\[.*\]);`
- **CSRF 复刻**:对齐目标行为(cookie+字段双校验,POST 成功后刷新 token);下单类接口防刷保留(目标限速,重建也限)
- **Windows 原生 curl 写中文路径失败**(`D:\渗透\...` No such file)→ 先下到英文 ASCII 路径再 cp
- **订单/业务数据走明文 GET 的复刻**:参数格式(如 `ordata[sn]=`)要与线上一致,前端 JS 依赖该格式跳转

