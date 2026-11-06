## 一、上传点完整攻击面

### 1.1 上传位置识别
| 位置/场景 | 测试要点 |
|----------|---------|
| 头像/图片上传 | 扩展名校验、图片二次渲染、图片马 |
| 附件/文档上传 | 白名单绕过、Office宏、PDF JS |
| 富文本编辑器 | CKEditor/UEditor/KindEditor历史漏洞 |
| 导入/批量上传 | CSV/Excel/XML外部实体导入 |
| 插件/主题上传 | CMS模板/插件上传直接拿Shell |
| 压缩包上传 | Zip Slip目录穿越、压缩包解压WebShell |
| 头像裁剪 | 裁剪后文件名/路径控制 |
| Base64上传 | JSON中base64字段、文件名参数可控 |
| URL远程抓取 | SSRF+上传（fetch remote url）|
| 分片上传 | 分片合并逻辑、文件名重组 |
| 云存储直传 | OSS/COS/S3签名直传，Bucket ACL配置 |
| WebDAV上传 | PUT/MOVE方法 |
| 日志/配置导入 | 特殊配置文件上传（.htaccess/.user.ini/web.config）|

### 1.2 防护层级识别
```
Layer 1: 前端JS校验（最易绕过）
Layer 2: 后端扩展名校验（黑名单/白名单）
Layer 3: MIME类型校验（Content-Type）
Layer 4: Magic Bytes/文件头校验
Layer 5: 文件内容检测（关键字扫描/沙箱）
Layer 6: 图片二次渲染（GD/ImageMagick）
Layer 7: 文件重命名（随机文件名）
Layer 8: 存储目录分离（非Web目录/CDN/OSS）
Layer 9: WAF/IPS流量检测（multipart解析、内容特征）
Layer 10: 中间件解析安全（handler映射）
```

