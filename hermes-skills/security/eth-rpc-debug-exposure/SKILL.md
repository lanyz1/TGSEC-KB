---
name: eth-rpc-debug-exposure
description: >-
  Use when 交易所/钱包/公链项目把 Ethereum/BSC RPC 节点开在公网：debug 命名空间未关，可
  debug_traceCall 取执行轨迹；错误信息与路径回显构成磁盘 oracle；配合热钱包地址与 txpool 归集。
---

# 公网 ETH/BSC RPC 节点暴露

## 探测
- 端口：8545/8546（HTTP/WS）、8551（engine）、9545（BSC）
- `POST / {"jsonrpc":"2.0","id":1,"method":"web3_clientVersion","params":[]}`
- `{"method":"rpc_modules"}` → 看是否返回 `debug`、`admin`、`personal`、`txpool`

## 高价值方法
| 方法 | 用途 |
|---|---|
| `debug_traceCall` / `debug_traceTransaction` | 全执行轨迹，含内部调用与 storage 读写 |
| `eth_getProof` | 直接验证任意账户/存储槽 |
| `txpool_content` / `txpool_inspect` | 待打包交易 → 归集地址、热钱包拓扑 |
| `admin_peers` / `admin_nodeInfo` | 节点内网 IP、enode、版本 |
| `personal_listAccounts`（老 geth） | 节点托管账户 |
| `eth_accounts` | 解锁账户（可直发交易） |

## 磁盘 oracle
- 错误里回显绝对路径（`/data/geth/...`、`/root/.ethereum/...`）→ 确认宿主用户与数据目录
- 与 `eth_getProof`/trace 的 `error` 字段组合，逐字符确认文件存在性（类似 SQLi 布尔）
- 目标若同时开 SSH，用户名为 `geth`/`bsc` 时优先试 key 与弱口令

## 归集与资金面
- `txpool_content` 拉出待处理交易的 `from/to/value` → 热钱包与归集路径
- 结合链上浏览器核余额（只读），不构造任何转账
- 交付口径：地址、余额、节点版本、暴露方法列表

## 判据
- `rpc_modules` 含 `debug` 且 `debug_traceCall` 返回 `structLogs` → 面成立
- 仅 `eth_*` 公开 → 只能读链上公开数据，不算暴露面
