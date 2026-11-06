/**
 * TikTok Cookie 采集浏览器守护（生产用纯 JS 版，node 直接运行，pm2 托管）
 * 用法（生产 .env）：
 *   TIKTOK_CDP_BIN=/opt/chromium/chrome-headless-shell-linux64/chrome-headless-shell \
 *   TIKTOK_CDP_PORT=9223 pm2 start node --name tikflow-cdp -- scripts/start-cdp-browser.cjs
 *
 * 为什么独立进程：Next.js instrumentation.ts 会同时编译 edge 版本，
 * import node:child_process 会让 edge-instrumentation.js 编译崩溃（全站 500）。
 * 坑: pm2 start node -- <相对路径> 按 pm2 cwd(/root) 解析 → MODULE_NOT_FOUND，
 *     必须传绝对路径 /srv/tikflow/scripts/start-cdp-browser.cjs
 */
const { spawn } = require("node:child_process");
const { existsSync } = require("node:fs");

const bin = process.env.TIKTOK_CDP_BIN;
const port = Number(process.env.TIKTOK_CDP_PORT) || 9223;

if (!bin || !existsSync(bin)) {
  console.error("[cdp] TIKTOK_CDP_BIN 不存在或未配置: " + bin);
  console.error("[cdp] 生产用 Chrome-for-Testing headless shell，勿用 snap chromium（AppArmor 限制 remote-debugging-port 不监听）");
  process.exit(1);
}

const child = spawn(
  bin,
  [
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-dev-shm-usage",
    "--remote-debugging-port=" + port,
    "--remote-allow-origins=*",
    "--user-data-dir=/tmp/tikflow-cdp",
    "about:blank",
  ],
  { stdio: "inherit" },
);

console.log("[cdp] Chromium 启动中: " + bin + " :" + port);
child.on("exit", (code) => {
  console.error("[cdp] Chromium 退出 code=" + code);
  process.exit(code ?? 1);
});
process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
