## Next.js 14 集成 CDP（工程坑,2026-08 实测）
- **webpack 不认 `node:` 前缀**:`node:child_process` / `node:crypto` → `UnhandledSchemeError`。修复见 `references/nextjs-14-browser-automation.md`
- **instrumentation.ts 会同时编译 edge 版本**:register() 里 import node:child_process → `edge-instrumentation.js` SyntaxError → **全站页面 500**(登录 API 200 但页面全挂,症状隐蔽)。修复:浏览器启动移到独立脚本 `scripts/start-cdp-browser.ts`(pm2/tsx 托管),instrumentation 只消费 CDP 端口(`if (NEXT_RUNTIME !== "nodejs") return` 只防运行不防编译)
- **puppeteer-core v24 类型需 ES2015+ target**:单文件 lint 报 node_modules 类型错是假警报(不读 tsconfig skipLibCheck),以项目级 `npx tsc --noEmit` 为准
- **作品列表代码化后 `json_200_` 空 body（已定位，2026-08 最终结论）**:手工 CDP 成功但 puppeteer 代码化后 fetch 空——试过 `networkidle2`、goto→reload、`waitForFunction('window.byted_acrawler.frontierSign')`+600ms、额外 4s 延时,**全部无效**。最终 CDP 诊断(主 tab 复测同样空)确认根因是**异地 IP 风控**(见 Pitfalls),不是时序。判别法:**先主 tab 手工复测**——空=风控(别改代码),有数据=才查时序/参数

