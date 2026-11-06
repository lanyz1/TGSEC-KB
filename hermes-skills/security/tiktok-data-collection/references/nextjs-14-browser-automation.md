# Next.js 14 集成 puppeteer-core / CDP 浏览器自动化

来源: TikFlow(TikTok 投流平台) 2026-08 实测,全部是真坑。

## 坑 1: webpack 不认 node: 前缀
```ts
import { spawn } from "node:child_process";  // → UnhandledSchemeError
import { randomUUID } from "node:crypto";     // → 同上(lib 被客户端组件引用时)
```
错误: `Module build failed: UnhandledSchemeError: Reading from "node:child_process" is not handled by plugins`
修复 next.config.mjs:
```js
experimental: {
  instrumentationHook: true,
  serverComponentsExternalPackages: ["child_process", "puppeteer-core"],
},
webpack: (config, { isServer }) => {
  if (isServer) {
    // ★对象形式 = commonjs require 加载，跳过 module concatenation 分析
    // 字符串形式("node:http")会报 "node:http for concatenation" 构建失败
    config.externals.push(
      { "node:child_process": "commonjs node:child_process" },
      { "node:fs": "commonjs node:fs" },
      { "node:path": "commonjs node:path" },
      { "node:os": "commonjs node:os" },
      { "node:crypto": "commonjs node:crypto" },
      { "node:url": "commonjs node:url" },
      { "node:net": "commonjs node:net" },
      { "node:stream": "commonjs node:stream" },
      { "node:util": "commonjs node:util" },
      { "node:events": "commonjs node:events" },
      { "node:buffer": "commonjs node:buffer" },
      { "node:http": "commonjs node:http" },
      { "node:https": "commonjs node:https" },
      { "node:zlib": "commonjs node:zlib" },
      { "node:worker_threads": "commonjs node:worker_threads" },
      "puppeteer-core",
      "socks",   // ★socks 包 require('net'/'stream') 不带 node: 前缀，webpack 服务端构建解析不了 → 也必须 external
    );
  }
  return config;
},
```
- 症状判别:`Module not found: Can't resolve 'net'` + `Import trace: ./node_modules/socks/...` = 该 npm 包依赖 Node 内置模块且被 webpack 打进 bundle → 把它加进 externals
- 引入新依赖的 node 生态包(如 `socks`)后**必须重跑 `npm run build` 验证**,再部署——本地 typecheck 过不代表 webpack 打包过

## 坑 2: instrumentation.ts 同时编译 edge 版本(症状最隐蔽)
- register() 里 `await import("node:child_process")` → 编译产物 `edge-instrumentation.js` 语法错误
- **表现**: 登录 API 正常 200,但所有页面 500;日志 `⨯ Error [SyntaxError]: Unexpected token ':' ... edge-instrumentation.js`
- `if (process.env.NEXT_RUNTIME !== "nodejs") return;` 只防 edge **运行**,不防 edge **编译**
- **修复**: 进程启动移出 instrumentation → 独立脚本 `scripts/start-cdp-browser.ts`(pm2/nohup 托管):
```ts
// scripts/start-cdp-browser.ts (tsx 运行)
import { spawn } from "node:child_process";
const child = spawn(process.env.TIKTOK_CDP_BIN!, [
  "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run",
  "--disable-dev-shm-usage",
  "--remote-debugging-port=" + (process.env.TIKTOK_CDP_PORT || "9223"),
  "--remote-allow-origins=*",
  "--user-data-dir=/tmp/tikflow-cdp", "about:blank",
], { stdio: "inherit" });
```
- instrumentation 只注册定时刷新器,`cdpConfigured()` 读 env 判断

## 坑 3: puppeteer-core 类型
- v24 类型用 `#private` 标识符 → 需 TS target ES2015+(项目 target ES2021 OK)
- write_file/patch 的**单文件 lint**(`tsc --noEmit file.ts`)不读 tsconfig 的 skipLibCheck → 报一堆 node_modules 类型错是假警报;以项目级 `npx tsc --noEmit` 为准

## 坑 4: images.remotePatterns
TikTok 封面/头像域名需加白名单否则 Next Image 报错:
```js
images: { remotePatterns: [
  { protocol: "https", hostname: "*.tiktokcdn.com" },
  { protocol: "https", hostname: "*.tiktokcdn-us.com" },
  { protocol: "https", hostname: "*.tiktokcdn-in.com" },
]}
```

## 坑 5: tsx 调试脚本
- `tsx -e "..."` 的 top-level await **静默失败**(无输出无报错)→ 改用临时 .mts 文件
- tsx 不解析 `@/` alias → 测试用相对路径 import;或用 vitest(模块解析正确)
- MSYS `/tmp` 对原生工具不可见 → 脚本放项目目录
- .mts 与 .ts 的 CJS/ESM 混合坑:`import ... from "./x.ts"` 报 "does not provide an export" → 用 vitest 跑采集层测试最省事

## 部署(Linux 服务器)
```bash
apt install -y chromium-browser   # 或 chromium
# .env:
#   TIKTOK_CDP_BIN=/usr/bin/chromium
#   TIKTOK_CDP_PORT=9223
pm2 start "npx tsx scripts/start-cdp-browser.ts" --name tikflow-cdp
```
- headless 模式签名是否过风控**未实测**:本地用有头 Chrome 验证成功;服务器若失败改 xvfb-run 有头
