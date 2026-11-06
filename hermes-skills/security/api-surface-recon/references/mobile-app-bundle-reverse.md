# 移动 App 客户端逆出 API 基址与端点表

前提：官方商店的 App 包是**公开可下载**的，零成本拿，等价于一份免费源码 —— 当站点前台是静态 SPA、真业务 API 只在移动端时，这是最短路径。

## 1. 取包

- `https://d.apkpure.net/b/APK/<package>?version=latest` → 常直接给 `.xapk`（zip，内含 base.apk + split）
- 备选：apkcombo / apkmirror / 官网下载直链；下完 `ls -l` 对 content-length（几十 MB 正常）
- Ghost 坑：包名用 `network.snp.android` 这类，页面标题和直链里的包名要一致

## 2. 先判框架，再选工具（不判框架 = 白跑）

```bash
unzip -l base.apk | grep -E 'assets/(index.android.bundle|www/)'
# dex 含 com/facebook/react → React Native；libapp.so → Flutter；仅 classes*.dex → 原生
```

| 框架 | 配置在哪 | 工具 |
|------|----------|------|
| 原生 | `classes.dex` 字符串 | `strings classes.dex \| grep -oE 'https?://[a-z0-9.-]+' \| sort -u` |
| React Native | `assets/index.android.bundle`（Hermes 字节码，非文本 JS） | `hbc-disassembler` |
| Flutter | `libapp.so` | `strings libapp.so` / 专用工具 |
| Cordova | `assets/www/*.js` | 直接读 |

**对 React Native 应用跑 dex `strings` 会得到「包里没有后端地址」的错误结论** —— dex 里只有库常量。

## 3. Hermes bundle 反汇编

```bash
pip install hermes-dec        # 提供 hbc-disassembler / hbc-decompiler（或 hbctool）
hbc-disassembler bundle.bin out.hasm     # 5MB bundle → 70MB+/百万行 .hasm，正常
```

Hermes 字符串表是**连续存放**的，正则一次能抓出整块配置对象：

```bash
rg -o 'https?://[A-Za-z0-9.-]+' out.hasm | sort -u
rg -o '"/(v[0-9]|api|auth|account|wallet|settings|profile|ads)[A-Za-z0-9/_.:{}$-]*"' out.hasm
rg -o '.{0,60}(baseURL|apiKey|API_KEY_HEADER|x-key|secret|Bearer).{0,60}' out.hasm
```

要点：
- 直接对 .hasm 用 ripgrep，不要试图「反编译成可读 JS」—— 字符串表就够挖端点和配置。
- **抓到的 key 先判来源**：大量是 SDK 的公开 demo key（Alchemy / ethers 示例等），看相邻字符串是不是库名，再决定当不当战果。把 SDK key 报成「目标密钥」是自伤。
- 同一 bundle 里常同时存在多个 base URL（主站 API / core API / mobile API / 广告 API）—— 全部记下，逐一探活。

## 4. 拿到 base URL 后的第一轮

按顺序试（常零鉴权）：`/openapi.json`、`/docs`、`/redoc`、`/actuator`、`/metrics`、`/healthcheck`、`/settings/*`。
一份裸放的 `/openapi.json` = 全端点表 + 参数模式，直接和从 bundle 抄的清单做差集找未文档化端点。

## 5. 与 SPA chunk 交叉

App 里常内嵌 WebView 后台或引用同一个 Angular/React 后台。把 App 里逆出的 API 前缀拿去打后台域名的 chunk（见 SKILL.md 第 2 节），两边端点表合并后再做差集。

## 6. 产物

- 端点表 + 每个端点的鉴权形态（无鉴权 / 业务级错误 / 框架 401）
- 完整 base URL 列表 + 服务器指纹（`Server` 头、错误体格式）
- 落盘：`PROOF_<wave>_apk_endpoints.json`（端点、方法、请求体形状、响应码），供后续复打与报告引用
