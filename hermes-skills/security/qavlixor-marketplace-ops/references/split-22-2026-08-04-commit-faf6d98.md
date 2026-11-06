## 代码史山清理(2026-08-04 首轮,commit faf6d98)
已清(低风险,均有引用实据):`app/seller/_preview/`(2 样板页)、`seller-refresh.css`/`seller-shopify.css`/`seller-polaris.css`(polaris 类名全仓 tsx **0 命中**,去 layout import)、`SellerDepositRequestButton`/`SellerDepositRefundActions`(零引用)、`packages/domain/`(全仓 0 引用空壳)、根目录 0 字节垃圾文件、tsconfig.tsbuildinfo。
待单开一轮(高风险):`lib/local-db.ts` SQLite 镜像逻辑(10+ API 引用,需重构直读 Prisma)、scripts/ 一次性运维脚本归档、work/backups/ tmp/ outputs/ 清理、i18n 生成文件入库问题、`.next-build`/`.next-dev` 缓存(dev 在跑不能动)。

### 死代码排查技巧
- **CSS 假活跃判定**:grep 出 css 选择器 `grep -oE "^\.[a-zA-Z0-9_-]+" file.css`,再逐个查 tsx 引用 `grep -rln "class.*$c" app/ components/`。0 命中 = 可删(即使仍被 layout import,如 seller-polaris.css)。
- **组件零引用判定**:`grep -rn "ComponentName" app/ components/ | grep import` 无结果即可删。
- 删文件用 `git rm`(自动暂存删除);已删文件再 add 用 `git add -u`。

### ⚠️ 特殊字符文件名坑(本次踩)
- 根目录垃圾文件 `{console.error(e)` 实际是 **17 字符含右括号** `{console.error(e)` — `git rm`/`find -delete`/`node unlink` 全失败(pathspec 不匹配/MSYS glob),用 **python `os.unlink('{console.error(e)')` 强删** 成功。
- 排查时用 python `repr(os.listdir)` 看真实字节,别信 ls 显示。
- **`git add -u` 会把工作区所有已修改文件暂存**(包括 C 阶段未确认的 globals.css)!只 add 本次清理文件时逐个列路径,或用 `git restore --staged <file>` 撤回误暂存。

