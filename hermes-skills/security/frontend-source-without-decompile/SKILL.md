---
name: frontend-source-without-decompile
description: Use when 只有dist/APK却要前端原工程. 四路求源码.
triggers: 前端源码, npm run build 原工程, 不要 hashed JS, 不要 smali, sourcemap, 只有 dist, 前端工程缺失, .vue 源码
---

# 前端原工程获取：不靠反编译的四条路

## 适用场景
客户/交付要求「可 `npm run build` 的原工程，不要 hashed JS、不要 smali」，
但手上只有容器里的 nginx dist、ASAR 解包产物、APK 反编译。

## 铁律
**先在包内穷尽证明「源码确实不在」，再去外网找。** 否则会把「没找全」当成「没有」。

### 包内四路穷尽（缺一不可）
```bash
# ① 原生源文件
find <tree> -name "*.vue" -o -name "*.tsx" -o -name "*.jsx" | wc -l
# ② 构建配置（真工程必有）
find <tree> -name "package.json" -o -name "vite.config.*" -o -name "vue.config.js" | wc -l
# ③ sourcemap（有 map = 等价拿到源码）
find <tree> -name "*.js.map" | wc -l
# ④ git 打包态（.vue 藏在 git 对象里，find 看不到！）
find <tree> -type d -name ".git" | wc -l
find <tree> -name "*.bundle" | wc -l
```
**关键坑**：`find -name "*.vue"` 只扫工作树。源码若以 git 对象/packed 形式存在，
必须用 `git log --all --name-only` / `git ls-tree -r <branch>` 才看得到。
**判断 dist 能否还原**：看 `package.json` 有无 + `.js` 是否 Vite/webpack 压缩。
Vite 产物特征：`import"./vendor.vue/vendor.vue.<hash>.js";import{M as e,N as t}`。
无 sourcemap + 已压缩 ⇒ **静态不可还原**，转外网四条路。

---

## 外网四条路（按可行性排序）

### 路 1：证书透明度 → 找出厂商全部公网主机【最容易被忽略，命中率最高】
```bash
# 主域与其关联域都要查
curl -s "https://crt.sh/?q=%25.<domain>&output=json" | python -c "
import json,sys
for e in json.load(sys.stdin):
    for n in (e.get('name_value') or '').split(chr(10)):
        n=n.strip().lower()
        if n and '*' not in n: print(n)
" | sort -u
```
**要点**：
- 证书里的子域 ≠ 有 DNS 记录，但仍要逐个解析（很多只差 DNS）
- 发现 `dev.` / `test.` / `demo.` / `prod.` 命名空间 = **dev 环境常无鉴权、常带 sourcemap**
- 厂商常有**多个关联主域**（如 `linksoft.cn` 与 `linknet.ltd`），**必须都查** —— 前端常挂在其中一个上
- 产品名/租户名也可能自成域名，一并向 crt.sh 提交

### 路 2：sourcemap 直取【dev 环境常开】
```bash
# 先取首页拿真实 chunk 名（构建 hash 与包内那份不同，必须现取）
curl -sk "https://<host>/" | grep -oE 'src="[^"]+\.js"'
# 再要同名 .map
curl -sk -o /dev/null -w "%{http_code} %{size_download}\n" "https://<host>/assets/<chunk>.js.map"
```
**要点**：
- **必须用线上首页的真实文件名**，不能拿本地 dist 的名字硬套
- 404 是常态，但**成本极低，必须试**
- 命中即得 `sourcesContent` = **原始 `.vue`/`.ts` 全文**，一次成型

### 路 3：Vite/webpack dev server【命中=原始源码】
```bash
for p in /@vite/client /src/main.js /src/main.ts /src/App.vue /vite.svg /package.json /.env; do
  curl -sk -o /dev/null -w "$p %{http_code}\n" "https://<host>$p"
done
```
**判断**：首页引 `./assets/index.<hash>.js` = nginx 托管的 build（非 dev server）；
引 `/src/main.js` 或 `/@vite/client` 存在 = **dev server 在跑 ⇒ 源码全文可取**。

### 路 4：运行时内省【拿不到 .vue 文件但能拿等价工程】
首页可开、JS 已压缩、无 map、无 dev server 时的**唯一可行路径**。
让应用自己把结构交出来（不碰二进制，不算反编译）：
```js
// 浏览器控制台 / CDP Runtime.evaluate
const app = document.querySelector('#app').__vue_app__;
// 全部路由
app.config.globalProperties.$router.getRoutes()
// 组件树 + props + state（递归遍历 vnode）
app._instance.subTree
// Pinia 全部 store 及其 state/getters/actions
app.config.globalProperties.$pinia._s
// i18n 全量文案
app.config.globalProperties.$i18n.messages
```
**另加 XHR/fetch hook** 抓全部接口 + 真实 payload：
```js
// 在页面加载前注入
const of = window.fetch; window.fetch = (...a) => { console.log('REQ', a); return of(...a); };
const ox = XMLHttpRequest.prototype.open;
XMLHttpRequest.prototype.open = function(m,u){ console.log('XHR', m, u); return ox.apply(this, arguments); };
```
**产出**：全部路由 + 组件树 + 状态机 + 接口契约 + i18n ⇒ **功能等价、可 `npm run build` 的重写工程**。

---

## ★ 从压缩 bundle 里能「合法」榨出什么
即使无 sourcemap，bundle 本身就是账本：
```bash
# 全部 API 路径（往往上百条）
grep -oE '"/[a-zA-Z0-9_/-]{4,60}"' bundle.js | sort -u
# 全部中文文案（简繁双语 i18n）
grep -oE '"[^"]*[一-鿿][^"]*"' bundle.js | sort -u
# 构建期绝对路径 → 暴露源码根目录
grep -oE '[A-Za-z0-9_/.-]{0,40}\.vue' bundle.js | sort -u
```
`/app/src/App.vue` 之类字符串 = 构建容器里的源码路径，直接告出源码根。

---

## 判定口径（对客户怎么说）
| 情形 | 结论 |
|---|---|
| 有 `.vue`/`package.json` | 原工程在，直接给 |
| 有 `.js.map` 或能取到 | **等价原始源码**，可交付 |
| dev server 在跑 | **原始源码**，可交付 |
| 只有压缩 bundle + 活站点 | **可重写功能等价工程**；原文件必须向厂商索取 |
| 什么都没有 | 只能索取源码仓 |

## 常见坑
- **别把「本地 dist 的文件名」当线上文件名**，hash 不同，必须现取首页
- **别只查一个主域** —— 厂商常有多主域，前端挂在另一个上（`linksoft.cn` vs `linknet.ltd`）
- **公网 DNS 里指向私有 IP 的记录**（如 `gitlab.x.cn → 10.0.0.120`）说明服务内网专用，外网无路，别浪费时间
- **同一台公网 IP 可能用 vhost 服务多个域名**：用 `curl -H "Host: <域名>" https://<ip>/` 试；
  但若不同 Host 返回**完全相同**的响应，说明不是 vhost 路由，停止猜测
- **goproxy/nexus 之类的「public」子域**多半只是公网镜像，拉不到私仓；`not found` 秒回即证实
- **`find -name "*.vue"` = 0 不等于源码不在** —— 必须先看 `.git`/`.bundle`
- cron/后台脚本落盘用明确的 `D:/路径`；
  Windows 下 native curl **不认 `/tmp`**，会静默写失败
