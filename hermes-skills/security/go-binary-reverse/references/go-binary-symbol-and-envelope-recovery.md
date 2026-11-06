# Go 二进制符号/信封恢复实测记录（2026-09-26）

两例：① Android 定制 Clash 内核 `libclash.so`（ARM64，PIE，用于签名/注册密钥）；
② Linux Go agent `agent.bin`（x86_64，用于运维云控信封）。

## 例 1：libclash.so（ARM64，符号未 strip）
- `pclntab` 搜索时先找 `\xf1\xff\xff\xff`；因 PIE `.so` 的 offset 基准是 pcHeader 自身，
  用「函数名前缀 = `main.*` / 入口前是 `ret`」两个判据校正基准后，导出：
  `main.getSS1@0xb217c0`、`main.getSS2@0xb218c0`、`main.getRegisterKey@0xb219c0`、`main.getRegisterKiv@0xb21ac0`，
  符号表还包含 `main.isValidSignature`。
- `pip install capstone` 后 ARM64 反汇编这四个函数 ⇒ 看到 key/iv 由调用方传入。
  **结论直接改变路线**：不去逆算法，改为下远端配置 `bzyregister.txt`/`ymregister.txt`/`hostdef.txt`，
  一次拿到 key、iv、固定推广 userId、`reg.<品牌>.win/com` 注册域。
- 静态爆破（`.so` 内 15k 候选串 → 两阶段 300 万组合）**全 0 命中** ⇒ 密钥运行时计算，归档此结论。

## 例 2：agent.bin（x86_64 Go agent）信封
- 接口 `/api/agent/heartbeat|report|tasks`，字段 `envelope`，格式最终定为：
  `json.Marshal → aes.NewCipher(key) → 随机 iv → pkcs7Pad → AES-CBC → base64`，外层 `{"iv":b64,"payload":b64}`。
- 误判纠偏顺序：先猜 AES-GCM（多编码变体全 `invalid`）→ 用 pclntab 定位 `main.pkcs7Pad/pkcs7Unpad`
  ⇒ **PKCS7 = CBC**，不再在 GCM 上打转。
- key：从 agent 参数提取的 32 字符串不是密钥；pclntab 追到 `0xa312a0` 是 `crypto/rand.Reader`（**诱饵**）；
  key 实为运行时堆指针 ⇒ **静态不可得**，写清结论收手（可选方向：面板下发通道 / 它的 state 文件）。
- 可复用判据：*静态候选全 0 命中 + key 来自堆写入* ⇒ 别再爆，转向通道。

## 例 3：PC 端 Tauri（BZY.exe + verge-mihomo.exe）
- 12MB 前端 `BZY.exe` 里 `strings` 得参数名 `channelId/plat/ver/platver/br/md/selectNodeId`；
- 更新源 `https://raw.githubusercontent.com/darkSuperman/updater/` ⇒ 全下其仓库，得 10 个品牌的
  `update.json/updatebzy/updatejm/…`（品牌矩阵 + 渠道号 + 分发域）；
- 仓库里的 minisign 公钥 = 分发链归属证据（写报告用）。

## 工具环境
- `pip install capstone`（本次 5.0.9）；本机无 pip → 用 `python3 -m venv` 或 uv。
- 大文件解包：`unzip`/`7z` + `npx asar extract`；Android 用 `apktool d`。
- Python 读大 `.so` 字节时用 `errors='replace'` 并跳过空行/`\x00`，否则解析器会因非法续行崩掉。
