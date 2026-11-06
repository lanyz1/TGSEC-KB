## 九、修复建议

**多层防御方案：**
1. **白名单机制**：严格白名单限制允许的扩展名（不要用黑名单）
2. **文件重命名**：使用随机文件名（UUID/时间戳+随机数），保留原始文件名但不作为访问路径
3. **MIME验证**：使用finfo_file（PHP）/MimeMapping（.NET）读取文件真实MIME，而非信任Content-Type头
4. **Magic Bytes验证**：使用getimagesize()/文件头校验
5. **内容检测**：扫描恶意代码特征（但需注意免杀对抗）
6. **存储隔离**：上传文件存储到独立域名/CDN/OSS，不在Web可执行目录
7. **禁止执行**：上传目录配置为`php_flag engine off`（Apache）/移除handler映射
8. **图片二次渲染**：使用GD/ImageMagick重新处理图片（破坏图片马）
9. **文件大小限制**：限制上传文件大小
10. **WAF规则**：配置multipart解析规则，检测双filename、超长头等
11. **中间件加固**：
    - 关闭PUT/MOVE方法（WebDAV）
    - 配置cgi.fix_pathinfo=0（PHP）
    - 正确配置handler映射，避免多扩展名解析
    - 禁止.htaccess覆盖（AllowOverride None）
    - 限制.user.ini使用
12. **权限最小化**：Web进程低权限运行，上传目录不可执行

