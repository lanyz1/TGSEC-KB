# Cloudflare Turnstile Workflow（无感 · 两世代加密）

Cloudflare Turnstile 托管挑战（managed challenge）前端加密与协议逆向。两个世代：8/11（RC4 世代）与 8/14（TEA 世代，约 12h 轮换）。

## 挑战流程与端点链

1. `GET /cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1?ray={ray}` → 227KB 编排 JS（指纹 + FO 管线，~12h 轮换）
2. `POST /cdn-cgi/challenge-platform/h/g/fo/{id}:{ts}:{sig}/{ray}/{cH}` → 第一轮 FO（URL 末段 = cH，头带 `cf-chl: cH`）
3. `GET challenges.cloudflare.com/turnstile/v0/g/{sitekey}/api.js`
4. `GET .../turnstile/f/av0/rch/{id}/{sitekey}/light/fbE/new/normal`
5. `POST .../fo/...`（第二轮 FO，turnstile 域）
6. `GET .../pat/{ray}/{ts}/{hash}`（PAT token）
7. `GET brunhild.../i/{ray}/{token}`（CORS 探测）
8. `GET .../ci/{ray}/{ts}/{token}` → `Set-Cookie: cf_clearance`

## 第一代：自定义 RC4 流密码（8/11 build）

- 常量：eC 149/15/175/107/114，eZ 149/111/200（8/14 新 build 轮换为 142/98/114/205/18）
- 初始化：`h = seed & 0xFF`（seed = cH 首字节）；`i=210^h, l=174|h, j=129|h, m=53^h, S=[0]*256`
- eC 轮：`IE = Ix ^ ((v+149)&0xFF) ^ 15 ^ m; IH = Ix ^ ((v-149)&0xFF) ^ 175 ^ m; m ^= Ix ^ ((107+v)&0xFF) ^ 114; S[m] ^= (IH^IE)`
- eZ 轮：`IE = Ix ^ ((v-149)&0xFF) ^ 111; m ^= Ix ^ ((v-149)&0xFF) ^ 200; swap(S[IE], S[m])`
- 密钥流：每字节 `ie,ih = eC(); eZ(); out = ie ^ ih`
- 旧 body 格式：JSON指纹 → RC4.xor(seed) → base64url → 每50字符 `$` 分隔 → `$$` → SHA256(明文) 签名段（RC4 加密）

## 第二代：FO TEA 管线（8/14 build，12h 轮换）

body 管线：
1. 计数器字节：首字节 = `FM<<Fu`（旧窗口 32）
2. payload → JSON 字符码序列化；数据帧 = `[32] + JSON字节 + [32]`
3. 转义段 = `[253,1,flag]` + 内容；len≥128 时 DEFLATE `Z_FIXED`（固定 Huffman，首字节 0x53）——**默认动态 Huffman 会被服务端 400 拒绝**
4. 填充 `pad=(8-len%8)%8` 补 0
5. 头部：random128 = 128B getRandomValues；`enc = BigInt(random128)^65537 mod N`（RSA 裸模幂，N=1024bit）；header[128]=pad
6. `key16 = random128[40+9*pad:+16] XOR "VoEfnuGLrjstqMiZ"`（16B 固定 XOR 密钥）
7. `state = FH(key16 4 字, pad)`（TEA-delta 0x9E3779B9 字展开，64 字）
8. 分块每 8B，`keyExt[idx*64..+64] = FQ(state, idx)`（每块 64 字密钥流）；encryptBlock 32 轮 Feistel
9. 自定义 65 字符字母表（取前 64）6-bit 查表 b64（每窗口轮换）

FH 字展开：`KE += delta; Ko[KH++] = u32(KE + (Kh? Y:KM:KV:Kt))`，共 64 字。

FQ 密钥派生：两段 32 轮流式密钥 Feistel，段1 起点=块索引、段2 起点=(idx+1)&255。

encryptBlock：`KM += ((((J<<4)^(J>>>5))+J) ^ key)` —— **注意括号**：JS 中 `+` 优先级高于 `^`，实际为 `KM + (F(J) ^ key)`，不是 `(KM+F(J)) ^ key`（首版移植踩坑）。

## 响应解码 tO

- 200 响应：标准 base64 ~113.5K 字符
- `xY = 32 ^ XOR((cRay+"_") 每字符)`
- `out[i] = ((b[i] - xY - (i%65535) + 65535) % 65535) % 255`
- 明文 ~85KB latin1 = runProgram VM 程序（运行时反序列化解释器，无源码定义）

## Worker 指纹（11 条消息，反 bot 核心）

- msg3 OPFS 文件系统 timing：`getDirectory→getFileHandle→createSyncAccessHandle→write+flush` 同步刷盘耗时（真机 0.1-0.5ms）
- msg4 Timer 分辨率：5000 次 performance.now() 双采样最小差（真 Chrome 0.003-0.01ms）
- msg10 WASM CPU benchmark：SIMD(i32x4/f64x2)，常数 0x9e3779b9，4 函数轮流

## 轮换机制与重新逆向 playbook

- 主轮换 ~12h：更换密码常量、b64 字母表、VM 字节码、WHtx4 XOR 密钥、RSA 模数、计数 BigInt、payload 字段名
- 稳定不变：FO 管线结构、TEA delta 0x9E3779B9、tO 解码逻辑、端点结构
- 触发信号：POST /fo/ 返回 400，或 fetchedAt 超 12h，或 orchestrate 源码字母表正则不命中
- 重新逆向：正则提取字母表(`` `[A-Za-z0-9$+\-]{64,66}` ``)/cH/cRay/md → Node 构建 → 浏览器兜底注入探针(P5 payload捕获/P8 运行时字符串表2200条) → 写 .cf-fo-params.json → 实弹 200

## 绕过结论

- 纯协议 cfauto：Node 构建 body + 住宅代理轮转 → FO 全部 200 + tO 解码
- 完整绕过：cloakbrowser(真实 Chromium TLS) + 住宅 socks5 → cf_clearance → 同会话 reload 200
- 纯 curl 复用 cf_clearance → 403（clearance 与 TLS/JA4 + __cf_bm/cf_chl cookies 绑定）
