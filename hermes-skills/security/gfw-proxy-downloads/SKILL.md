---
name: gfw-proxy-downloads
description: >-
  测绘引擎·Use when downloading GFW-blocked files/APKs via local proxy.
owned: true
tier: ops
pack: survey-skill
---

# gfw-proxy-downloads（测绘引擎）

本卡已收编为测绘引擎作业卡。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/gfw-proxy-downloads/`

溯源（仅标记）：`hermes/networking`

---

# 被墙官网文件下载（本机代理通道）

本机在中国（GFW），很多官网直连失败。v2rayN 常驻运行（xray/sing-box，端口等环境事实见 `v2rayn-proxy-diagnostics`）。本技能覆盖：探测封禁 → 走代理抓取 → 解析 JS 动态加载的下载链接 → 哈希校验。适用于 signal.org、GitHub releases、Google Play APK 等被墙站点的官方文件。

## Workflow

1. **探测封禁**：`curl -sL -o /dev/null -w "HTTP:%{http_code}" <url> --max-time 30` → `HTTP:000` = 网络层失败（被墙/DNS），别傻重试，直接走代理。
2. **探本机代理端口**：
   ```bash
   for p in 7890 7891 10808 10809 1080 8080; do timeout 2 bash -c "echo > /dev/tcp/127.0.0.1/$p" 2>/dev/null && echo "OPEN $p"; done
   ```
   - 本机实测：**10808 可直接当 HTTP 代理用** `curl -x http://127.0.0.1:10808 ...`（115MB+ 大文件下载也没问题）。
3. **走代理抓页面**：`curl -sL -x http://127.0.0.1:10808 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" <url> -o <dest>` — 一定要带 UA，部分 CDN/WAF 拒 curl 默认 UA。
4. **JS 动态加载的下载链接**：页面显示 "Loading..." 或按钮 href 不在 HTML 里 = 链接由 JS 填充。抓页面源码找 JSON 接口：
   - `grep -oE 'getJSON\("[^"]*"' page.html` → 例：`https://updates.signal.org/android/latest.json`
   - 模板引擎（mustache.js）渲染按钮：找 `id="template"` 块看 URL 拼法。
   - **别猜旧 URL 规律**——实测可能已 404（Signal 旧名 `signal-website-universal-release-*.apk` 已死，现行是 `Signal-Android-website-prod-universal-release-{ver}.apk`）。
5. **完整性校验**：
   - 先 HEAD：`curl -sIL -x <proxy> <url> | grep -iE "^HTTP|content-length"` 确认 200 + Content-Type（APK 应为 `application/vnd.android.package-archive`）+ 大小。
   - 官方 JSON/API 若给 `sha256sum`，下载后 `sha256sum file` 逐字符比对——这是官方认可的完整性凭据。

## Pitfalls

- `HTTP:000` 是网络层失败，不要原地重试，改走代理。
- 链接发现优先 curl+grep，别用 browser_exec：其首次使用要用户批准远程调试（chrome://inspect 弹窗），会打断用户。
- 大文件走代理慢（115MB ≈ 5 分钟），用 `curl -#` 带进度条、给耗时预估，禁止静默下载（用户铁律）。
- git-bash 下临时文件用 `$LOCALAPPDATA/Temp` 而非 `/tmp`（原生工具读不到 MSYS 路径）。
- 国内手机端装 Signal 等被墙应用：手机也要挂代理才能注册/同步，电脑下好 APK 只是第一步。

## 参考

- `references/signal-android-apk.md` — Signal 安卓官方 APK 完整实测（latest.json 结构、URL 规律、证书指纹、下载命令）
