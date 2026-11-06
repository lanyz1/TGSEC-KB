<!-- archived from /root/.hermes/skills/security/http-method-webdav/SKILL.md on 2026-10-21 -->

---
name: http-method-webdav
description: >-
  HTTP 方法与 WebDAV 面。触发：OPTIONS Allow、TRACE、TRACK、PUT 上传、
  PROPFIND、MKCOL、MOVE、WebDAV、XST。ownCloud 预签名走专卡。
  落马走 file-upload-testing。
---

> 归档卡：原目录 `/root/.hermes/skills/security/http-method-webdav`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/http-method-webdav/…')`，不要相对 `references/legacy/` 解析。

# HTTP 方法 / WebDAV

目标须在 `config/scope*.json`。默认只写 marker，不 DELETE。

## 真源

- 手法：`docs/playbooks/测绘引擎HTTP方法与WebDAV作业手法.md`
- 工具：`python3 tools/ops/http_method_surface_probe.py --base https://授权站 --case <案>`
- ownCloud：`owncloud-webdav-presign-bypass`

```bash
python3 tools/ops/http_method_surface_probe.py --base https://授权站 --case <案>
```

## 何时用

侦察看到 `DAV` 头、`Allow: PUT`、或目录面像静态托管。  
403 方法绕过另走 `401-403-bypass-techniques`。

## 失败

全是 `405`/`501` 才算阴性。WAF 吃掉 OPTIONS 换出口池再打一次。
