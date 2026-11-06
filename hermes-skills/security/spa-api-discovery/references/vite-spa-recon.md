# Vite 打包 SPA 侦察补充(KbitPay 管理台实战,2026-09)

本文件补充 SKILL.md 主流程之外的 Vite 构建 SPA 打法(与 webpack / Next.js 章节并列)。

## 识别 Vite

- 主入口 `index-*.js` 或 `index.<hash>.js`,HTML 里 `<script type="module" crossorigin src="./assets/xxxindex.xxx.js">`
- 主 JS 开头就是 `const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=[...]))...`
- 页面常带 `<link rel="stylesheet" crossorigin href="./assets/xxx.css">`

## 核心陷阱:chunk 引用在 `__vite__mapDeps` 里

Vite 的 chunk 文件名**不按常规格式**出现在代码里。grep `'"[A-Za-z0-9._-]+\.js"'` 会得到 **0 匹配**,让人误判"没有更多 chunk"。

真实结构:

```js
const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=[
"js/layouts.KrfFQ1v9.js","js/vue.runtime.esm-bundler.Bdb6_H3H.js",
"js/style.BTo3Vyw_.js","css/style.cyJZB4WD.css", ...
])));
```

- 真实 URL 都在 `m.f` 数组里,格式 **`"js/xxx.js"` / `"css/xxx.css"`(带 `js/` / `css/` 前缀!)**
- 动态 import 是反引号 + 相对路径:`import(`./layouts.KrfFQ1v9.js`)`,前缀 `./` = 站点根
- `__vite__mapDeps` 数组可能跨多行,包含 css

## 提取 + 下载命令

```bash
head -c 500 index.js   # 确认是 Vite(__vite__mapDeps)

# 提取全部 chunk 路径(带 js/ 前缀!):
grep -oE '"(js|css)/[A-Za-z0-9._-]+\.(js|css)"' index.js | sort -u > chunklist.txt

# 下载前缀 = 站点根 + js/xxx.js(不是 /static 或 /assets):
while read f; do
  url="https://$HOST/${f#\"}"
  url="${url%\"}"
  curl -sk --max-time 20 -o "$(basename $f)" "$url"
done < chunklist.txt

# 全量 grep API 端点:
grep -ohE '(webv1|api|v1)/[A-Za-z0-9_/-]{3,80}' *.js | sort -u
```

## 实战数据(KbitPay 管理台)

- index.js 610KB,初版正则 `'"[A-Za-z0-9._-]+\.js"'` → **0 匹配**(卡了一轮)
- 改提取 `__vite__mapDeps` 里 `"js/xxx.js"` → **163 个 chunk 全部下载**
- 全量 grep → **172 个 `/webv1/Admin*` 端点**(提现/商户/回调/系统用户等)

## 与 webpack / Next.js 对比

| 构建 | chunk 引用位置 | 提取正则 |
|------|---------------|---------|
| webpack | `webpackJsonp.push` 模块定义 | `static/js/[a-zA-Z0-9_.-]+\.js` |
| Vite | `__vite__mapDeps` 的 `m.f` 数组 | `"(js|css)/[A-Za-z0-9._-]+\.(js\|css)"` |
| Next.js App Router | `/_next/static/chunks/` 页面级分片 | `/_next/static/chunks/[^"]+\.js` |
