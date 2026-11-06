# Metro / Expo dev server 源码泄漏(React Native / 混合 App 实战)

2026-09 实证:目标 `45.13.59.23:8081` 是一个 **Expo SDK 54 / metro 开发模式打包服务器**暴露在公网。
拿到的不是"压缩 chunk",而是**未混淆全量业务源码 + source map 里的原始源码全文(含整个 node_modules)**。
这是移动端 / RN 应用最高价值的一类入口。

## 1. 识别

```bash
curl -s "http://TARGET:8081/status"     # → packager-status:running
curl -s "http://TARGET:8081/"           # → expo dev client 页 / "Cannot GET /"
curl -s "http://TARGET:8081/index.bundle?platform=android&dev=true&minify=false" -o bundle.js
```

- 端口常是 **8081**(metro 默认);`dev=true` 时 bundle **不压缩**,直接可读
- bundle 里搜 `/\.env`、`EXPO_PUBLIC_` ⇒ 直接拿到后端 URL + **项目根绝对路径**
  - 实测命中:`EXPO_PUBLIC_API_URL=https://api.<brand>.online`、`EXPO_PUBLIC_SOCKET_URL=...`,
    以及路径 `/www/wwwroot/<site>/VPS2/AppChattron/mobile` —— 连宝塔站目录、项目 slug/owner 一起泄漏
- 判定技术栈看 bundle 开头的 `exposdk:xx.x.x`

## 2. 金矿:source map 的 `sourcesContent`

bundle 末尾 `//# sourceMappingURL=`、或 `/index.map`、或 manifest 指到的 map 文件。
**每个源文件都带 `sourcesContent` 全文,且包含整个依赖树**:

```python
import json
m = json.load(open('wz.map'))                      # 实测 13,743,870 字节 / 1328 文件
srcs, cont = m['sources'], m['sourcesContent']
app = [i for i, s in enumerate(srcs) if '/node_modules/' not in s]   # 应用自有源码(本次 86 个)
for i in app:                                      # 按 srcs[i] 路径落盘
    ...
```

产物价值:
- **应用全量原始源码**:api client / socket 层 / encryptionService / 各 screen / store —— 协议、字段名、
  错误处理、隐藏功能全在里面
- **顺带白拿 vendor 源码**:要逆向目标所依赖库的协议时,直接读 map 里的 `socket.io-parser`、
  `engine.io-parser`、`axios` 等**原文**。跳板机常无 PyPI / CDN 不通(`curl unpkg` 只回 49 字节错误页),
  **本地 map 是唯一可靠信源** —— 本次正是靠它一次定死了 socket.io v4 二进制事件组帧规则
- 列 map 的 `sources` 还能反推项目结构(`src/api/`、`src/screens/`、`src/services/`),给出攻击面清单

## 3. 坑

- **密钥扫描别用窄 grep**:`grep -v '^    '` 这类缩进过滤会把命中整行吃掉,得出"没有密钥"的假结论。
  **直接全文打印关键文件**(`.env`、`src/constants/config.ts`、`src/api/apiClient.ts`、socket/加密模块)更可靠
- 输出被截断时:改「URL/路径清单 + 极短脚本」或分行短写,不要一次抓太多
- `minify=false` 不是必须,但能显著提升可读性;`dev=true` 才是关键

## 4. 价值链(重点)

dev server 常与**生产 vhost 同机**:
1. map 给出后端 API 域名 → 立刻确认它是否解析回**同一 IP**(本次 `api.<brand>.online` 与赌场生产站同机)
2. 同机 ⇒ 源码泄漏直接升级为「**同机文件写入 → 读各站 Laravel `.env` → 生产 DB 凭据**」的提权链
3. 项目根绝对路径给出宝塔布局,便于推断同机其他站与 webroot 位置

## 5. 关联

- 后端若是 socket.io action-RPC,协议细节见
  `websocket-encrypted-protocol-reverse/references/socketio-v4-action-rpc.md`
  (组帧规则、必发 `40` CONNECT 包、二进制事件类型必须为 `5`、ack 是数组、drain 不能提前 return)
