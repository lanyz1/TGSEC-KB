# pnpm 项目迁移到新目录(Windows)— 2026-08-04 实测

场景:把 Next.js + pnpm 项目整个目录复制到新路径(如 `D:\Codex\qavlixor-marketplace` → `D:\跨境商城\qavlixor-marketplace`)。

## 结论先行
**不要复制 node_modules,直接在新位置 `pnpm install` 重装。**
robocopy 复制 node_modules 后,pnpm 的符号链接结构(顶层 `node_modules/*` → `.pnpm/` 内真实包)会失效,`pnpm dev` 会触发 `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`(要交互确认删目录但无 TTY),且 `Cannot find module '.prisma/client/default'`。

## 正确步骤(实测通过)
```bash
# 1. 复制源码 + .git + 缓存(排除 node_modules)
robocopy "<src>" "<dst>" /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NP /XD node_modules .next-build .next-dev .git
robocopy "<src>\.git" "<dst>\.git" /E /COPY:DAT /R:1 /W:1 /NFL /NDL /NP
# (可选)复制 .next-dev 缓存:robocopy "<src>\.next-dev" "<dst>\.next-dev" /E ... /MT:16

# 2. 删掉复制来的 node_modules(链接已坏),重装
rm -rf "<dst>/node_modules"
cd "<dst>"
CI=true pnpm install --frozen-lockfile   # 本地 store 硬链接,秒装(本项目 5.9s)

# 3. 重新生成 Prisma client(重装后 .prisma/client 丢失)
# ⚠️ 本项目是"双轨"schema:provider=postgresql(生产真源)但本地 DATABASE_URL=file:./dev.db(SQLite)。
#    直接 pnpm prisma:generate 会生成 postgresql 版 client → 启动后所有 prisma 调用报:
#    "Error validating datasource `db`: the URL must start with `postgresql://`"
#    首页可能仍 200(页面缓存/不查库),但 /api/* 与查库页面持续报错,症状隐蔽!
#    正确做法:先停 dev → 临时改 provider=sqlite → generate → 还原 provider → 重启 dev
sed -i '0,/provider = "postgresql"/s//provider = "sqlite"/' prisma/schema.prisma
CI=true npx prisma generate
sed -i '0,/provider = "sqlite"/s//provider = "postgresql"/' prisma/schema.prisma
git diff --stat prisma/schema.prisma   # 应为空(schema 保持 postgresql 不变)

# 4. 清 .next-dev 缓存(避免旧编译产物引用旧路径),再起 dev
rm -rf .next-dev
pnpm dev
```

## 关键坑
1. **pnpm 的 node_modules 是符号链接结构**,robocopy 复制过来链接目标无效 → 必须重装而不是复制。pnpm store 在 `D:\.pnpm-store`,`pnpm install --frozen-lockfile` 走硬链接,不额外占空间。
2. **prisma generate 必须重跑**:重装后 `node_modules/.prisma/client` 不存在,页面 500 `MODULE_NOT_FOUND: .prisma/client/default`。
3. **停 dev 换位置时,process kill 只杀 shell 包装**,`next dev` 子进程残留占 3000 端口 → 新 dev 静默换到 3001(bash 输出有 `Port 3000 is in use by process <pid>`)。
   清端口:`netstat -ano | grep ":3000.*LISTEN"` → `MSYS_NO_PATHCONV=1 taskkill /F /PID <pid>`(MSYS 下双斜杠写法 `//F` 会被路径转换吞掉)。
4. 中文路径在 MSYS bash 里要用引号:`cd "/d/跨境商城/qavlixor-marketplace"`。
5. robocopy 退出码 0-7 都是成功(1=有复制),8+ 才是失败。
6. **双轨 generate 的 EPERM**:dev 运行中 generate 会报 `EPERM: operation not permitted, rename ... query_engine-windows.dll.node`(engine dll 被 dev 进程锁)。必须先停 dev(用 `MSYS_NO_PATHCONV=1 taskkill /F /PID <监听pid>`)再 generate。
7. **`.env` 文件带 BOM**:本项目 `.env` 第一行是 `\ufeffDATABASE_URL`(utf-8 BOM),prisma CLI 读 `.env`(非 `.env.local`)也能解析,但用 grep/sed 匹配 `^DATABASE_URL` 会失败(前面有隐藏 BOM 字符)。排查 env 时用 python `open(f, encoding='utf-8-sig')` 或 `grep -oE "^[A-Z_]+"` 看键名,别信 `grep '^DATABASE_URL'` 无结果=没配置。
8. **症状识别**:迁移后首页 200 但 API/查库页 500 + 日志 `Error validating datasource` → 99% 是双轨 generate 问题(不是代码 bug,不是服务器问题)。

## 验证
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/   # 200
# 买家页 200;seller/account/admin 307(未登录中间件跳转,正确行为)
# 探针复测确认样式改动仍生效(globals.css 的改动随源码一起复制)
```
