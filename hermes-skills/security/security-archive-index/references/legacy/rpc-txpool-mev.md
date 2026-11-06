<!-- archived from /root/.hermes/skills/security/rpc-txpool-mev/SKILL.md on 2026-10-21 -->

---
name: rpc-txpool-mev
description: >-
  区块链 RPC 节点 txpool 暴露 + MEV 三明治攻击面检测。
  触发：域名含 -mainnet / -rpc / node. / rpc.；响应含 jsonrpc / Geth / Bor / reth /
  Erigon / Nethermind；POST 返回 JSON-RPC；端口 8545/8546/30303；
  web3_clientVersion / txpool / mempool / pending transactions / MEV / sandwich。
  见到区块链 RPC 端点立刻按本卡检测，禁止只测 eth_blockNumber 结案。
---

> 归档卡：原目录 `/root/.hermes/skills/security/rpc-txpool-mev`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/rpc-txpool-mev/…')`，不要相对 `references/legacy/` 解析。

# 区块链 RPC txpool MEV 攻击面

**来源**: token.im 案 (2026-09-02) — imToken 公开 RPC 暴露 txpool + sendRawTransaction，构成完整 MEV 基础设施。

## 成功口径

| 档 | 成立 | 不算 |
|----|------|------|
| L1 | `web3_clientVersion` 返回节点信息 | 只能 `eth_blockNumber` |
| L2 | `txpool_status` 或 `txpool_content` 可读 | 只有版本信息 |
| L2b | `txpool_content` + `eth_sendRawTransaction` 均可用 = **CRITICAL MEV** | 只有 txpool 无 sendRawTx |
| L3 | 解码出 DEX swap 交易 + 计算 sandwich 利润 | 有 txpool 但无 DEX 交易 |

## 检测流程

### Step 1: 节点指纹

```bash
# 确认 JSON-RPC 可用
curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'

# 预期: {"result":"Geth/v1.x.x/linux-amd64/go1.x.x"} 或类似
```

常见节点类型:
- `Geth` — go-ethereum（BSC fork / ETH mainnet）
- `Bor` — Polygon
- `reth` — Paradigm Rust 客户端（Base/OP）
- `Erigon` — 高效全节点
- `Nethermind` — .NET 客户端
- `Tenderly` — 模拟/代理（通常无 txpool）

### Step 2: txpool 暴露检测

```bash
# txpool 状态（轻量）
curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"txpool_status","params":[],"id":1}'
# 预期: {"result":{"pending":"0x1a","queued":"0x6ef"}}

# txpool 完整内容（重量级，可能数 MB）
curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"txpool_content","params":[],"id":1}'
```

**关键判断**: 返回 `result` 且含 `pending`/`queued` 字典 = txpool 暴露。返回 `error` "method not found" = 已禁用。

### Step 3: 交易提交检测

```bash
# 发一个格式错误的 tx 测试端点可用性
curl -s -X POST "$RPC_URL" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_sendRawTransaction","params":["0xdead"],"id":1}'
```

**判断**:
- `unmarshal transaction failed` / `rlp: value size exceeds` / `failed to decode` = **端点可用**（CRITICAL）
- `method not found` / `not supported` = 已禁用
- `the method does not exist` = 已移除

### Step 4: 管理接口暴露

```bash
for method in eth_accounts net_peerCount admin_peers admin_nodeInfo \
  debug_traceTransaction txpool_inspect eth_mining eth_coinbase eth_sign; do
  curl -s -X POST "$RPC_URL" \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":[],\"id\":1}"
done
```

**高危方法**:
- `admin_peers` / `admin_nodeInfo` → 网络拓扑泄露
- `eth_sign` / `personal_sign` → 可代签交易
- `debug_*` → 执行跟踪、状态读取
- `miner_*` → 挖矿控制

### Step 5: DEX Swap 识别（仅 txpool 暴露时）

已知 DEX Router 地址:

| DEX | 链 | Router 地址 |
|-----|-----|-------------|
| PancakeSwap V2 | BSC | `0x10ed43c718714eb63d5aa57b78b54704e256024e` |
| PancakeSwap V3 | BSC | `0x13f4ea83d0bd40e75c8222255bc855a974568dd4` |
| Uniswap V3 | ETH/Polygon | `0xe592427a0aece92de3edee1f18e0157c05861564` |
| Uniswap Universal | Multi | `0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45` |
| QuickSwap V2 | Polygon | `0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff` |
| SushiSwap | Multi | `0x1b02da8cb0d097eb8d57a175b88c7d8b47997506` |
| Paraswap V5 | Multi | `0xdef171fe48cf0115b1d80b88dc8eab59176fee57` |

Swap Method ID:
- `0x38ed1739` = swapExactTokensForTokens
- `0x7ff36ab5` = swapExactETHForTokens
- `0x18cbafe5` = swapExactTokensForETH
- `0x791ac947` = swapExactTokensForTokensSupportingFee
- `0x414bf389` = exactInputSingle (V3)
- `0x5ae401dc` = multicall

过滤 txpool 中 `to` 匹配 Router + `input` 前 4 字节匹配 Method ID = 可被三明治的 swap。

## 等级判定

| 组合 | 等级 | 说明 |
|------|------|------|
| txpool_content + sendRawTx | **CRITICAL** | 完整 MEV 基础设施，直接资金损失 |
| txpool_content 可读，sendRawTx 禁用 | **HIGH** | 信息泄露（交易隐私、策略泄露） |
| txpool_status 可读 | **MEDIUM** | 统计级泄露 |
| 仅 clientVersion/peerCount | **LOW** | 运维信息泄露 |

## 多链扫描模板

对 Web3 项目，枚举所有链的 RPC 端点（常见命名模式）:
```
{chain}-mainnet.{domain}
{chain}-rpc.{domain}
mainnet-rpc.{domain}
rpc.{domain}
node.{domain}
```

常见 chain: `eth` / `bsc` / `polygon` / `arbitrum` / `optimism` / `base` / `avalanche` / `fantom`

## 三明治攻击利润估算

```
每笔 sandwich 利润 ≈ swap_value × slippage_tolerance × pool_depth_factor
典型范围: swap 金额的 0.1% ~ 0.5%
```

影响因子:
- 池子深度（TVL 越小利润率越高）
- 滑点设置（用户设高滑点 = 更多利润空间）
- 其他 MEV bot 竞争（降低实际利润）
- gas 成本（BSC 极低 ~0.05 Gwei；ETH 主网高）

## 不走这张卡

| 指纹 | 走 |
|------|-----|
| Spring Boot /actuator | `spring-gateway-actuator-killchain` |
| REST API 无认证 | `api-security` 或九阶段全文 |
| GraphQL 暴露 | `graphql` 相关 Skill |
| WebSocket RPC | `websocket-pentest` |

## 真源

- 手法：`docs/playbooks/打网站手法.md`
- 工具：`python3 tools/ops/core_web_surface_probe.py --help`


---

## 外部库增量（2026-10-11 分享包）

## debug 命名空间利用（自建节点主战场）

**核心原语**：Geth 的一批 `debug_*` 方法**接收文件路径参数**，把分析产物写到**服务器任意路径** ⇒
**任意路径文件覆写（内容固定为 Go pprof 二进制，不可控）**。是"写"不是"读"，但用错误语义差分就是**文件系统 oracle**。

```bash
# 成功 = {"result":null}；同时 = 在目标机上新建/覆写了该路径
curl -s -X POST "$RPC_URL" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"debug_writeMemProfile","params":["/tmp/x"],"id":1}'
```

### 磁盘 oracle：五态差分（不用 RCE 就能画出文件系统）

| 返回 | 含义 |
|---|---|
| `{"result":null}` | **路径可写**（新建或覆写成功） |
| `is a directory` | 该路径是**已存在目录**（不能当文件写） |
| `no such device or address` | 该路径是 **socket / 设备**（如 `geth.ipc`）⇒ 确认 IPC 存在与命名 |
| `permission denied` | 存在但**当前进程用户无权限** ⇒ 精确暴露权限边界 |
| `no such file or directory` | 父目录不存在（该目录树不存在） |

一次请求 = 一个 bit 的结论。扫几百条路径就能画出：运行用户(`geth`/`bsc`)、HOME、datadir、chaindata、keystore 目录、`.bashrc/.profile/.bash_history`、`password.txt`、`config.toml`、`jwtsecret`、`nodekey`、`start.sh`、`docker-compose.yml`；以及**被拒目录**（`/usr/share/nginx/html`、`/etc/nginx`、`/etc/cron.d`、`/root`）——
这组结果直接给出"任意写能不能变 RCE"的判决。完整方法矩阵 + 扫路径清单见 `references/geth-debug-arsenal.md`。

### 覆写靶标矩阵（写成功 ≠ 拿到 shell）

| 靶标 | 效果 | 有条件 RCE？ |
|---|---|---|
| `jwtsecret` / `nodekey` / `genesis.json` / `config.toml` / `password.txt` | 节点失联、engine API 认证坏、重启即挂 | 否（自毁型） |
| `keystore/UTC--*` | 破坏账户 keystore ⇒ 资产永久锁死。**授权下也严禁** | 否，破坏性 |
| `~/.bashrc` `~/.profile` | 等运维下次登录触发 | **是（等触发）** |
| `authorized_keys` / `crontab` / `cron.d` / systemd unit | 持久化 + 定时执行 | **是（等触发）**，但常 `permission denied` |
| 站根 / 反代目录 `/usr/share/nginx/html` | 落 webshell | **是**，但常被拒（权限边界） |
| `/tmp` `/dev/shm` | 落点，配合 trace/日志口 | 否 |

**内容不可控 ⇒ 单靠这一原语不能 RCE**。判定纪律：能写 + 有执行触发点 + 有权限 = RCE；三者缺一就诚实写
"任意路径写入(内容不可控)，未达成 RCE"。别把"写成功"吹成 getshell（用户会纠正）。

### 其余高危 debug 方法

| 方法 | 危害 |
|---|---|
| `debug_setHead(<n>)` | **链头回滚**（主网节点回滚 = 数据不一致；破坏性，授权下也不轻易动） |
| `debug_standardTraceBlockToFile` / `standardTraceBadBlockToFile` | 往 datadir/`/tmp` 批量落盘（Bitpie 一次写出 104 个文件）⇒ 占满磁盘 + 暴露节点路径 |
| `debug_freeOSMemory` | 强制释放/GC ⇒ 抖动 DoS |
| `debug_startCPUProfile` / `stopCPUProfile` / `cpuProfile(file,sec)` | 同任意路径写 + 拖 CPU |
| `debug_verbosity` / `vmodule` | 调日志级别 ⇒ 日志刷爆，且后续请求参数会进日志 |
| `debug_chaindbProperty` / `chaindbCompact` / `dumpBlock` / `printBlock` | 磁盘布局 + **出块 coinbase** + 链数据泄露 |
| `debug_traceCall` / `traceTransaction` / `storageRangeAt` / `accountRange` | 全链状态查询（没有 txpool 也能做链上情报） |

## 热钱包资金测绘（txpool 归集法）

**链路**：`txpool_content`/`txpool_inspect` 拿待处理交易 → 按 `to`/`from` 做**频次统计** →
出现次数最高的少数地址 = 资金中枢（热钱包/归集器）。比拿地址表去猜准得多。

| 角色 | 判据 |
|---|---|
| 主/副热钱包 | `to` 频次最高 + 余额大 + 大量小额入账 |
| 大额归集 | 余额极大但入账笔数少（大额低频） |
| 扫拢器 | 全是**出账**（待发出），余额只留 gas |
| 合约 | `eth_getCode` 非空（USDT/USDC/DEX router） |

余额：`eth_getBalance` 查主链币；`eth_call` + `balanceOf` 查 ERC20：
```bash
# data = 0x70a08231 + 地址左补 0 至 32 字节
curl -s -X POST "$RPC_URL" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_call","params":[{"to":"<token合约>","data":"0x70a08231<32字节地址>"},"latest"],"id":1}'
```
- ETH 主网 USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7`、USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`；BSC-USDT `0x55d398326f99059fF775485246999027B3197955`
- **`eth_accounts` 通常为 `[]`** ⇒ `eth_sign`/`eth_signTransaction` **签不动**。结论只能写"可监控不可动"，别写成"可转走资金"
- 与 `wallet-exchange-fund-verification` 分工：那边是**有内账/凭据**时查资产；这边是**无凭据**时纯靠链上 + txpool 反推资金结构

## IPC / 本地面（往往才是真正的终点）

自建节点本机有 `geth.ipc`（Unix socket），**HTTP 关掉的 `personal`/`admin`/`miner` 在 IPC 上通常全开**：
- 探测：`writeMemProfile("<datadir>/geth.ipc")` 返回 `no such device or address` = **socket 存在**
- 能"动钱"的必要条件是**触到 IPC**：shell / SSRF 打 unix socket / 容器逃逸 ⇒ `personal_unlockAccount` + `eth_sendTransaction`
- 只有 HTTP 面 ⇒ 只能"看钱"。把"触到 IPC"写成复工条件，而不是编一个不存在的 RCE

## 等级判定 / 定级与红线

| 组合 | 等级 | 说明 |
|------|------|------|
| txpool_content + sendRawTx | **CRITICAL** | 完整 MEV 基础设施，直接资金损失 |
| txpool_content 可读，sendRawTx 禁用 | **HIGH** | 信息泄露（交易隐私、策略泄露） |
| txpool_status 可读 | **MEDIUM** | 统计级泄露 |
| 仅 clientVersion/peerCount | **LOW** | 运维信息泄露 |
| **debug 开且敏感路径可写** | **CRITICAL** | 节点可被自毁/覆写；是否 RCE 另判 |
| debug 开但只有 `/tmp` `/dev/shm` 可写 | **HIGH** | 有写原语、无执行触发点 |
| 热钱包全量测绘(角色+地址+余额) | **HIGH** | 资金面情报，可监控不可动 |

- `debug` 开 = HIGH/CRITICAL 起步；但没有"内容可控 + 执行触发点"就**不写 getshell**
- 破坏性操作（`setHead`、覆写 `nodekey`/`jwtsecret`/`keystore`、`freeOSMemory`）**先答"能不能恢复"，默认不做**
- 只读优先：`eth_*` / `trace*` / `txpool_*` 只读；`debug_write*` 只在授权明确且先用 `/tmp` 验证

## 资产发现：空间测绘三路（找不到端点时先走这里）

引擎只发 GET，链节点 RPC 必须 POST ⇒ **引擎结果永远只是候选**，收口必须用本卡自带脚本：

```bash
python3 scripts/rpc_node_probe.py --targets candidates.txt --delay 0.5 --out probe.json
python3 scripts/rpc_node_probe.py --selftest     # 无需外网，自证分类逻辑
```

可复制的三路粗筛语句（FOFA/Quake/Shodan/Censys/ZoomEye 字段全集 + 额度坑 + 实名/权限实测限制）、
以及 `GET → 200 空体`、`无 Server 头`、`405 method not allowed` 的**源码级指纹依据**：
`references/space-mapping-dorks.md`。

★现实：报告里的真目标是 **443 + nginx 反代 + 路径 `/eth`**，直接搜 `port:8545` 命中率近 0 ⇒
给定企业时走 **APK 签名 OU → 企业域 → crt.sh 全量历史子域 → `rpc.`/`trpc.`/`node.` 命名族 → cert 回灌引擎扩线**。

## Pitfalls

1. **写成功 ≠ 能读**。`debug_writeMemProfile` 只有写没有读回；`/home/bsc/mnemonic.txt` 返回成功只说明**这个路径可被写**，不证明服务器上原先存有明文助记词。别在报告里写"怀疑存有助记词且可读"。
2. **主机隔离要先判定**：ETH 节点写 `/home/bsc/` 返回 `no such file`、BSC 节点写 `/home/geth/` 返回 `permission denied` ⇒ 两台机或强隔离容器，别按同一台机推横向路径。
3. **`/tmp` 与 `/dev/shm` 几乎总可写**，而 `/usr/share/nginx/html` `/etc/nginx` `/etc/cron.d` `/root` 通常 `permission denied`——这组结果就是"任意写能否变 RCE"的判决书，必须实测不能推测。
4. **公开 RPC 与自有 RPC 要分清**：自有域名/CNAME 到自建 IP 的节点才是高价值面；公共 RPC 上打 debug 无意义（也不是目标资产）。
5. **`debug_writeMemProfile` 会真改磁盘**。探路径前想清楚：已确认的写点会把原文件变 pprof 垃圾（Bitpie 案覆写了 `jwtsecret`/`nodekey`/`config.toml`/`password.txt`/`genesis.json`）——**不可逆**。只读侦察优先，写点验证挑 `/tmp` 或明确可重建的文件。

## 支持文件

| 文件 | 内容 |
|---|---|
| `references/geth-debug-arsenal.md` | debug 命名空间方法矩阵（返回语义/危害/请求体）+ 磁盘 oracle 扫路径清单 |
| `references/bitpie-edifei-case.md` | Bitpie/edifei 案全文（RPC/热钱包地址/路径 oracle/后台/APK/CT），不脱敏 |
| `references/space-mapping-dorks.md` | **资产发现**：自建节点 RPC 的空间测绘语法（五家引擎）+ 源码级指纹依据 + 实测限制清单 |
| `scripts/rpc_node_probe.py` | 候选批量验证器：POST `rpc_modules`/`web3_clientVersion`/`eth_chainId`/`txpool_status` → 定链+定级（mock 自测通过） |
