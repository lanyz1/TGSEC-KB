# Qavlixor 生产部署（2026-08-06 首次实战）

## 服务器连接（关键）
- `root@202.95.1.135`，**SSH 端口 12125**（22/2222/22000/1022 全被安全策略拒绝——Connection closed/Error reading SSH protocol banner，不要浪费时间试标准端口）
- 密码：`~/.ssh/deploy_pw` 明文文件（本机已有），无 sshpass → 用 **python paramiko** 连接最稳
- 服务器环境：node v22.23.0、pnpm 11.5.3、PG 127.0.0.1:5432（qavlixor_prod）、磁盘 68G 空闲、**服务器无 git**（archive 部署正确）
- PM2：应用名 `tiktok-marketplace`，4 fork 实例（3000-3003）
- 项目目录 `/www/tiktok`，生产 distDir=`.next-build`（next.config.ts 里 dev 用 .next-dev）
- 历史备份模式：`/www/tiktok/backups/source-*.tgz`

## 部署流程（手册第 9 节 + 实战修正）
1. **本地打包**：`git archive --format=tar HEAD -o qav-deploy.tar`（注意 Windows git-bash 的 /tmp 不可写，放项目目录）
2. **备份**（手册强制）：服务器 `cp prisma/dev.db .env .env.local → backups/deploy-YYYYMMDD/`
3. **上传**：paramiko SFTP `sftp.put(qav-deploy.tar, "/tmp/qav-deploy.tar")`
4. **解压覆盖**：`cd /www/tiktok && tar xf /tmp/qav-deploy.tar`（保留 .env*、node_modules、.next-build、backups、prisma/dev.db——archive 不含 .env 天然安全）
5. **依赖**：`pnpm install --frozen-lockfile`（无新增依赖时秒过 "Already up to date"）
6. **prisma**：`pnpm exec prisma generate` + `pnpm exec prisma db push`（生产 PG；新表纯新增安全，不动存量）
7. **构建**：`nohup pnpm run build > /tmp/qav-build.log 2>&1 &` 后轮询日志（3-8 分钟）
8. **重启**：`pm2 restart tiktok-marketplace` + curl 健康检查 + `nginx -t`
9. **记操作日志**（docs/ops-log/）+ 本地 commit 部署前置提交

## 验证新表/新代码
服务器 node 脚本放**项目目录**跑（/tmp 下 require 不到 node_modules）：
```js
// /www/tiktok/check.cjs → node check.cjs && rm
const {PrismaClient}=require('./node_modules/@prisma/client');
const p=new PrismaClient();
const t=await p.$queryRawUnsafe("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename ILIKE '%buyer%'");
console.log(t.map(r=>r.tablename));
```
paramiko exec_command 传复杂引号会炸——脚本写成文件传上去再执行，别内联。

## 部署后热更新单个文件（不用整包重部署）
改单个脚本/配置时：`sftp.put(local, "/www/tiktok/<相对路径>")` 直接覆盖对应文件即可（如修复机翻脚本 `scripts/i18n-scan-lib.mjs`）。改 API/组件/页面仍需 build+restart；改**独立脚本**（cron 跑的 .mjs）上传即生效。改完手动跑一次验证（cron 会在下个周期自动用新文件）。

## 构建失败排障（cssnano "Unexpected '/'"）
症状：`pnpm build` → `HookWebpackError: Unexpected '/'. Escaping special characters with \ may help.` + 内层错误在 `static/css/<hash>.css:<line>:<col>`（Parser.combinator 上下文）。

关键事实：
- **dev 模式永不报**（dev 不跑 cssnano 压缩）——"dev 正常 + tsc 过 + build 挂"就是这类 CSS 问题
- 报错 line:col 指向的是**合并/转换后**的 CSS，不是源码行（675:27 实际是注释块里的字符位，无法直接映射回源码）
- `postcss.parse` 和 `next/dist/compiled/postcss-safe-parser` 都解析 OK——**只有 cssnano 挂**，所以别浪费时间去改"语法错误"

排障法（二分定位，~2 分钟）：
```js
const postcss = require('./node_modules/.pnpm/postcss@8.4.31/node_modules/postcss');
const cssnano = require('next/dist/compiled/cssnano-simple');
// 对单个 CSS 或合并片段跑：postcss([cssnano()]).process(css, {from:label})
// FAIL 的段再二分，直到定位到具体行区间
```
根因（本次）：`app/seller-proto.css` 里**注释块**含大量中文 + 全角括号 + `admin-review-*` 等字样（`*` 在注释里 + 老 cssnano 解析器把注释内容里的 `/` 误当选择器组合符）。**修复 = 把该注释块改写为纯 ASCII 安全格式**（拆短注释、去掉括号/`*` 连写）。
通用教训：往 CSS 注释里写长中文/带括号的说明有触发生产 build 失败的风险——注释尽量短 ASCII。

## 验证语言翻译已上线（bundle grep 法，2026-08 七国翻译部署实战）
UI 键翻译（translations.ts）是**客户端 LanguageSync 处理 data-i18n**——SSR HTML 不含翻译结果。所以：
- ❌ `curl -H 'Cookie: qavlixor-lang=es' ... | grep 西语词` 会空 → 这是**预期行为，不是部署失败**（SSR 只出默认语言/键名）
- ✅ 正确验证：grep 生产 bundle 是否含目标语言字符串：
  ```bash
  grep -rl 'Buscar productos, tiendas' /www/tiktok/.next-build/static/chunks/ | head -1
  grep -rl 'Añadir al carrito' /www/tiktok/.next-build/static/chunks/ | head -1   # 西语
  grep -rlE 'بحث عن المنتجات' /www/tiktok/.next-build/static/chunks/ | head -1   # 阿语
  ```
  全部命中 = 语言包已编译进客户端 chunk，线上切换语言即生效。
- **本机浏览器/curl 访问线上 202.95.1.135 HTTP 可能 000 空响应**（服务器对本机出口 IP 的来源限制——部署全程都这样，80 TCP 通但空响应；SSH 12125 不受影响）。**判断部署成功一律以服务器本地为准**：`curl 127.0.0.1:3000/` 200 + 自环 `curl http://202.95.1.135/` 200 + `pm2 list` 4 实例 online + bundle grep 命中。别把本机访问被拒误判为部署失败。

## 验证 UI 中文文案（SSR HTML 抓取法，2026-08-08 余额支付部署实战）
**与上面语言包验证相反**：组件里的中文文案（如结算页"余额支付"）grep static chunks **会落空**（webpack 压缩/unicode 转义/拆 chunk——原文和 `\u4f59\u989d` 转义形式都查不到）——**这不是部署失败**。可靠验证 = **登录态 node 脚本抓 SSR HTML**：
```js
// /www/tiktok/verify-ssr.cjs（登录 → GET 目标页 → 检查 HTML）
const l = await fetch(B + '/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:'<EMAIL-REDACTED>', password:'QaTest!2026', role:'buyer'})});
const cookie = l.headers.get('set-cookie')?.split(';')[0] || '';
const page = await fetch(B + '/checkout?product=<id>&sku=<sku>&qty=1', { headers: { cookie } });
const html = await page.text();
html.includes('余额支付');  // SSR 客户端组件初始渲染会输出中文原文
```
**验证方法论总结**：翻译字符串（LanguageSync 客户端处理，SSR 不含）→ chunk grep；组件中文文案（SSR 会渲染）→ SSR HTML grep。两者互补，用错方法会误判"没部署"。

## 部署后进程跑旧产物（时间戳对照法，2026-08-08 踩 2 次）
症状：新 API 生效（wallet 200）但前端 UI 没变（用户反馈"是不是没部署"）；或登录逻辑改了行为不变。
- **根因**：`pm2 restart` 时 build 可能还没真正完成（nohup 后台 build 的轮询日志"Compiled successfully"只代表产物写完，但若 restart 命令在 build 完成前发出/或 Next 增量缓存误判，进程加载旧产物）
- **排障**：`ps aux | grep next-server`（进程启动时间）vs `ls -la /www/tiktok/.next-build/BUILD_ID`（产物时间）——**产物时间 > 进程时间 = 进程跑旧产物 → 必须再 `pm2 restart` 一次**；还不行就 `rm -rf .next-build` 全量重建（29-30s）再 restart
- **同一 build 内 server/static 产物可能新旧不一**（增量 build 缓存 bug：API 路由新但客户端 chunk 旧）——只验证 API 通过≠前端已部署，UI 功能必须 SSR HTML 或浏览器实测
- **restart 后 ~12 秒内 API 可能返回 HTML/DOCTYPE**（进程未就绪瞬时现象）——重试即可，别误判服务挂

## gitignore 误伤 API 路由（2026-08-08 入驻上传 403 根因）
症状：某 API 的修复代码"已提交+已部署"，但生产行为不变（如入驻上传仍 403「商户入驻尚未审核通过」）——且之前明明验证过豁免在本地生效。

根因：`.gitignore` 的 `uploads/`（本意挡根目录本地存储目录）**匹配了 `app/api/uploads/` 目录** → 上传路由从不进 git → `git archive` 不含 → 服务器 tar 解压永远覆盖不到 → 生产一直是旧版文件（`ls -la` 时间戳 = 几周前）。

排查信号（三者齐备即确诊）：
1. `ls -la /www/tiktok/app/api/<路由>/route.ts` 时间戳很旧
2. 本地 `git ls-files app/api/uploads/route.ts` 无输出（未跟踪）
3. 本地源码有修复但服务器源码没有（`grep` 两边对比）

修复：
```bash
sed -i 's|^uploads/$|/uploads/|' .gitignore   # 精确化：只挡根目录
git add -f app/api/uploads/route.ts           # 强制跟踪
# 提交后重新打包部署
```

**通用防线（部署前 10 秒检查）**：`git archive` 打包后先验包：
```bash
tar tf qav-deploy.tar | grep app/api/uploads   # 应有输出；改了什么文件就 grep 什么
```
另：`.gitignore` 新增目录级规则后，跑一遍 `for d in app/api/*/; do git ls-files "$d" | wc -l` 扫未跟踪的 API 目录（0 = 被误伤）。

## 诚实汇报
部署中途 build 失败 → 服务器仍是旧代码在跑，**绝不能谎报"已上线"**。给用户：已完成步骤 / 失败根因 / 修复内容 / 剩余步骤，等确认继续。
