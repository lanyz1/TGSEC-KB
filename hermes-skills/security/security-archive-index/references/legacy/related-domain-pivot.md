<!-- archived from /root/.hermes/skills/security/related-domain-pivot/SKILL.md on 2026-10-21 -->

---
name: related-domain-pivot
description: "Use when mapping sibling domains or multi-entry fleets."
---

> 归档卡：原目录 `/root/.hermes/skills/security/related-domain-pivot`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/related-domain-pivot/…')`，不要相对 `references/legacy/` 解析。

# Related-Domain Pivot & Fleet Topology

从手里一个域，走到运营方的**全部相关域**，再用**一次请求**证明这些入口到底是不是同一个后端。

## 何时用

- 主站有多个兄弟入口（`api.` `hk-api.` `de-api.` `vip.` …），不确定是不是各自独立
- 枚举出的子域大部分没反应，但目标明显不止一个业务
- `robots.txt` / CNAME / 证书里出现了**当前域名之外**的名字
- 要写报告时需要回答“这几个域是不是一个东西”

## 一、向外扩：三个 pivot（都跑完再宣布资产图完成）

### 1. 展开 CNAME 目标，而不只是名字

子域 CNAME 指向**另一个 apex**，等于直接拿到运营方的另一个域名。新 apex 通常自带子域，要**递归**下去：

```bash
dig +short sub.target.com @1.1.1.1          # 看到 CNAME: cname.other.com
for s in other.com api.other.com img.other.com www.other.com; do
  printf "%-22s " "$s"; dig +short "$s" @1.1.1.1 | tr '\n' ' '; echo
done
# 新 apex 也要跑 crt.sh + 子域枚举
curl -s "https://crt.sh/?q=%25.other.com&output=json" | jq -r '.[].name_value' | sort -u
```

最后一步：**比对新 apex 的子域解析结果和手里已有的 IP**。指向同一台源站 = 同一套系统。

### 2. `robots.txt` 读全文，**尤其是 `Sitemap:` 那一行**

- `Disallow:` 行 = 真实路由表（`/create-order` `/search-order-by-*` `/user/`），比任何目录爆破都快
- `Sitemap:` 行常常指向**和当前探测域名不同的 apex**（你测的是镜像/别名，sitemap 指的是主门面）
- 顺着 sitemap 铺商品/资源列表，能反推 ID 空间与业务规模

### 3. 按证书分类每个入口，识别哪些没上 CDN

```bash
for h in $(cat live-hosts.txt); do
  printf "%-24s " "$h"
  timeout 10 openssl s_client -connect "$h:443" -servername "$h" </dev/null 2>/dev/null \
    | openssl x509 -noout -subject 2>/dev/null
done
```

| 证书形态 | 含义 | 优先级 |
|---|---|---|
| 每主机独立证书（`CN=api.target.com`） | CDN 前置，WAF/Turnstile 在前 | 常规 |
| 裸通配证书（`CN=*.target.com`） | **源站直出 TLS，无 CDN** | **优先** |

带通配证书的那组就是绕过 WAF 的现成通路，先打它们。

### 4. 运营者 GitHub 反查——个人 repo 是基建清单

子域 CNAME 指向 `*.github.io` 即拿到运营者 GitHub 用户名。立即拉该用户全部 repo 列表，并读每个 repo 的 `env/` 目录（`.env`、`.env.production`）：前端 repo 的 `VITE_*_BASEURL` 直接写着他们的另一套生产后端域名。每条新 URL 都是一个带独立凭据面的新目标——身份链（证书 CN → GitHub → .env → 新后台）比端口扫描的产出密度高。

```bash
curl -s "https://api.github.com/users/<owner>/repos?per_page=100" | jq -r '.[].name'
curl -s -H "Accept: application/vnd.github.raw" "https://api.github.com/repos/<owner>/<repo>/contents/env/.env"
```

个人 repo 也要快速定性：多为 fork/表白页/教程类无关项目——确认无关后立即回主线，不要在 repo 树里漫游。

### 5. 库凭据的「库归属」验证纪律

从 dev 库/heapdump 破解出的账号密码只在那个库对应的后端有效——拿去登生产端点会报密码错误（dev 库 sys_user 与生产库不互通）。先用登录端点的存在性 oracle（「账号不存在」vs「密码错误」）确认账号在当前后端存在，再消耗定向验证次数。同理，PG 登录角色是实例级：一个弱角色常能 `\c` 进同实例的多个库（含带 -dev 后缀但存着生产数据的库）——逐库枚举，跳过即漏整批资产。

## 二、拓扑定性：这些入口是不是一个后端？

**不要**把 N 个兄弟入口当 N 个目标逐个评估。一枚 token 发一次相同请求即可定性：

```bash
export TOK='<user jwt>'
for h in $(cut -d'|' -f1 live-hosts.txt); do
  printf "%-24s " "$h"
  curl -sk --max-time 12 -H "Authorization: Bearer $TOK" \
    "https://$h/api/v1/user/profile" | grep -oE '"(id|role)":[^,}]*' | tr '\n' ' '
  echo
done
```

- 各入口返回**相同 user id / role** → 共享用户库、**无数据隔离**。后果：
  - 一枚 token 通吃全部，资产档案里这些“独立目标”降级为“同一集群的入口”
  - **任一入口 admin 失守 = 全站失守**
  - 不需要逐个入口重做鉴权测试
- 返回 401/403 或不同 id → 至少数据面隔离了，再逐个测

脚本：`scripts/fleet_topology_probe.py`（见下）。

## 三、泛解析轮询池

CNAME 返回**十几条 A 记录** = CDN/负载池。逐个带 `Host:` 头打：

```bash
for ip in $(dig +short pool.example.com @1.1.1.1); do
  printf "%-16s " "$ip"
  curl -s -o /dev/null -w "%{http_code} " -H "Host: sub.target.com" "http://$ip/"
  curl -s -H "Host: sub.target.com" "http://$ip/" | head -c 60
  echo
done
```

响应一致 = 同一集群后端（任一 IP 直连即绕过 CDN）；响应不同 = 多后端混合，分而治之。

## 四、死资产纪律（省下几个小时）

| 现象 | 判读 | 动作 |
|---|---|---|
| crt.sh 有记录、但子域查不到 DNS | 记录残留，**已下线** | 直接剔除，不要指望隐藏端口/悬空 vhost |
| CNAME 能解析，但全端口关闭 | 陈旧目标（DNS 活、服务死） | 全端口扫一次确认后剔除 |
| IP 池里打出来是无关站点 | 同主机邻居（共托管） | 剔除，并在报告里写明理由 |

## 五、常见坑

- **裸通配证书 ≠ 同一台机器**，它只说明那组入口没走 CDN；证书可能由同一台 nginx 同时直出多个域，实际后端仍要靠 IP 解析确认。
- **泛 vhost 的 301 是噪声**：`nginx` 配了 `server_name _` 时，任意 `Host` 都会 301 到 `https://<host>/`。用**响应长度/正文**聚类分组判差异，只看状态码会把几十个假阳性当发现。
- **别把 CDN 轮询出来的 IP 当独立目标**：同池 IP 往往是同一后端，重复评估白烧时间。
- **同源多入口下，admin 面只需评估一次**：拿到一枚 token 后先跑拓扑矩阵，再决定是否逐域深入。
- **判定“不可达”前重试**：单次 000/超时可能是出口问题，至少重试 3 次或换出口交叉验证再定性。

## 六、产出要求

资产档案里必须显式区分：
1. **同一集群的多个入口**（写明共享哪些后端/用户库）——避免委托人误以为每个域都单独测过
2. **无 CDN 入口**（绕过 WAF 的通路）
3. **已剔除的死资产**（附剔除判据）

## 相关技能
- `web2-recon`（子域/CNAME/JS 面的发现管线）
- `target-profiling`（资产档案与攻击面整理）
- `telegram-shop-pentest`（站群里的发卡/账号商城变体）
- `cdn-origin-tracing`（把某个入口回溯到真源站）

## 支持文件
- `scripts/fleet_topology_probe.py` — 一枚 token 跑完整入口矩阵，输出是否共享后端
