---
name: aiowpm-secondorder-sqli-to-rce
description: "Use when 打 All-in-One WP Migration：窃 key 到 RCE。"
---

# All-in-One WP Migration 二阶 SQLi → 窃 secret_key → 未授权 RCE（CVE-2026-19949）

**CVSS 8.8**。插件 ≤ **7.109**，修复 **7.110**（2026-08-20）。研究者 Jack Taylor（Wordfence 赏金）。

## 四步链（这个链的设计才是可迁移的）

```
1. 埋雷  wp-trackback.php?p=<公开文章> 发 trackback
          blog name → comment_author，尾字符写 \
          URL      → comment_author_url，带 SQL 片段
          WordPress 原样存库，不转义反斜杠
          第一次 trackback 当「定时炸弹」：故意超时（导入限制 10s）
          让 payload 在后续 pass 执行，那时 importer 已把 ai1wm_secret_key 写回 wp_options
2. 触发  管理员导出 + 恢复站点（这插件的日常操作）
          导入时脆弱正则重写 trackback 行，字符串边界翻转，payload 变成可执行 SQL
3. 外带  payload 把 ai1wm_secret_key 复制到一条已批准的 comment
          未认证的 comments REST API 直接读得到
4. RCE   admin-ajax.php?action=ai1wm_import
          注册时带了 wp_ajax_nopriv_ai1wm_import（匿名可访问）
          唯一门禁 ai1wm_verify_secret_key() —— 现在 key 已到手
          传自己的 .wpress，Ai1wm_Import_Mu_Plugins（链上优先级 270）
          解到 wp-content/mu-plugins/ → 下次加载即执行
```

## 可迁移点三条

1. **插件把 `wp_ajax_nopriv_*` 当内部接口用**——只要有任何一处泄露了它依赖的“密钥”，整个管理面就变成匿名面。搜 `wp_ajax_nopriv_` 是 WordPress 插件审计的第一个筛选器。
2. **导入器必然写 `mu-plugins`**。任何“导入/迁移/恢复”型插件，看它是否会释放 PHP 文件到可执行目录，以及有没有校验文件清单。
3. **二阶注入的入口不需要高权限**：trackback 是匿名的。“需要管理员导出”不是阻碍——那是这插件的常规运营动作。

## 判定与操作

```bash
curl -s https://<t>/wp-content/plugins/all-in-one-wp-migration/readme.txt | grep -i 'Stable tag'
# ≤ 7.109 → 中
curl -s 'https://<t>/wp-json/wp/v2/comments?per_page=100' | grep -o 'ai1wm[a-z_]*key[^"]*'   # 运气好直接有
```

## 坑

- 需要管理员**真的**做一次导出+恢复。没有这个动作链不成立。
- `ai1wm_secret_key` 在导出包里被**排除**，只在 importer 侧重写——所以不能从别人的导出包里拿。
- 7.110 之后 key 校验改成 hash_equals + 额外 nonce，链断。
