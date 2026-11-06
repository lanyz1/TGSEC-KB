## 服务端部署(headless 采集浏览器)
- **★snap 版 chromium 有 AppArmor 限制**:`--remote-debugging-port` 不监听(进程在、端口不通,curl 空)——服务器上勿用 snap chromium 做 CDP
- 正确:Chrome-for-Testing **headless shell** 独立二进制(`chrome-headless-shell-linux64.zip`,storage.googleapis.com,~100MB),解压到 /opt/chromium
- headless shell 运行依赖(Ubuntu 24.04):`libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2t64 libpango-1.0-0 libcairo2 libx11-6 libxcb1 libxext6 fonts-liberation`——**`libasound2` 在 24.04 改名 `libasound2t64`**(旧名无安装候选,apt 直接失败);缺库症状:binary 报 `error while loading shared libraries: libnspr4.so`(只列第一个缺的,实际可能缺一串)
- 服务器可能无 `unzip` → 用 `python3 -c "import zipfile; zipfile.ZipFile('x.zip').extractall('/opt/chromium')"`;CfT zip 解压后**二进制丢执行权限** → `chmod +x .../chrome-headless-shell`
- pm2 托管路径坑:`pm2 start node -- scripts/start-cdp-browser.cjs` 相对路径按 pm2 cwd(/root)解析 → **必须绝对路径** `pm2 start node -- /srv/tikflow/scripts/start-cdp-browser.cjs`
- 部署脚本陷阱:tar 包上传后**记得 `tar xzf` 解压**再 build(update.sh 模板易漏此步,漏了就是旧代码上线)
- 生产 .env:`TIKTOK_CDP_BIN=/opt/chromium/chrome-headless-shell-linux64/chrome-headless-shell` + `TIKTOK_CDP_PORT=9223`
- 浏览器守护:pm2 托管纯 JS 脚本 `scripts/start-cdp-browser.cjs`(node 直接跑,勿依赖 tsx):`TIKTOK_CDP_BIN=... TIKTOK_CDP_PORT=9223 pm2 start node --name tikflow-cdp -- scripts/start-cdp-browser.cjs`
- 应用侧只消费端口(`cdpConfigured()` 读 env),instrumentation 只注册刷新定时器(见 Next.js 工程坑)
- **live 测试隔离**:需真实 Cookie 的测试命名 `*.live.test.ts`(默认不被 vitest 收集),`TT_CK=... npx vitest run tests/.../xxx.live.test.ts` 手动跑,`describe.skipIf(!TT_CK)` 保护

