# 链上资金验证 + 资金盘定性 + 用户灌号统计(2026 QQLink/KbitPay 实战补充)

前端加密协议还原、JWT 伪造、管理台白名单绕过见 `vite-rsa-envelope-signing.md`。本文件补后半段:资金面验证方法论。

## 1. 资金盘定性(充值类型分布是核心证据)

- 内账(DB 余额) vs 链上真实资金严重脱节 = 资金盘
- **查充值表 type 分布**: `transfer`/`internalUid`/`redPacket` 是系统内部凭空记账(常上百万), `chain` 才是真实链上充值(常只有几百 USDT)。99% 资金 = 记账数字
- 出金链路: 用户提现 → 扣内账 → 审核 → 平台以商户身份调代付 API → 热钱包链上打币 → 回调
- 热钱包抽空 + 大量卡单(state=3 无 tx)+ 配置指向测试线 = "提不出钱"是资金结构问题, 不是代码漏洞
- 提现表 state×type: `chain` 是唯一真出金; transfer/redPacket/internal* 秒成功只是内账搬家

## 2. TRON 链上钱包验证(TronGrid)

- tronscan API(`api.tronscan.org`)限流/401 快; **TronGrid**(`api.trongrid.io`)wallet/triggerconstantcontract 稳定
- **visible=true 时 owner_address/parameter 全用 base58 地址**, 传 hex 报 `ParseException invalid address for field`(1:19 位置)
- USDT 合约 `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`, balanceOf parameter = 24 个零 + 40 hex 地址(64 hex)
- b58→hex 手写坑: `n.to_bytes(25,'big')` 对高位小地址错位, 需按前导 '1' 计数补零
- 交易历史 API 返回地址被截断显示, 需从原始字段拿完整地址; 时间戳 ms → 日期还原资金流时间线

## 3. BSC 链上钱包验证

- `bsc-dataseed.binance.org` 等常被墙(`Cannot assign requested address` = 端口池/网络限制), **`https://bsc-dataseed.bnbchain.org` 和 `https://bsc.publicnode.com` 可达**
- `eth_getTransactionByHash` 反查 `from` = 出款热钱包; 余额 `eth_call` balanceOf
- BSC-USDT 合约 `0x55d398326f99059ff775485246999027b3197955`

## 4. 资金归集追踪

- 热钱包 tx 历史 → 大额转出目标 = 归集地址(常已空)→ 充值方 = 上游入口
- **多链各查一遍**(只查一个链/一个地址就下"抽空"结论是错的)
- 热钱包只剩主链币(BNB/TRX 维持 gas)= 抽干特征

## 5. 用户真实性统计(戳穿灌号)

- 按 email 域名分组: 压测灌号常是 `@stress.test` 假域名(4.4 万/4.7 万)
- 按月 created_at 分布: 某月暴增 = 灌号时间点
- 活跃度交叉: 有登录日志/有余额/有充值/有提现的用户数 = 真实盘子规模(常 100~300 人 vs 注册 4.7 万)
- 真实活跃用户数 ≈ 登录过的人数, 不是注册数; 官网宣传数 vs 库内实际数对比

## 6. GVA 源码/文件溯源(exa_files 表)

- GVA 上传分片表 `exa_files`(file_name/file_path/chunk_total)记录历史文件读取/写入尝试, 是攻击史与文件位置地图
- chunk 路径 `./breakpointDir//<path>_<n>` 暴露 GVA 容器内文件操作; `file:///app/config.yaml` 类记录 = 之前会话通过 file:// SSRF 已读
- 业务上传文件在 `exa_file_upload_and_downloads`(url 字段), 文件实际存宿主机 `/home/file/upload/`
- 后端 Go 源码物理上不在服务器(编译进二进制), 只能 pclntab 反编译; 前端 JS 即源码可直接全量下载还原
- 管理台前端环境变量暴露后端 API: `VITE_APP_API_URL`/`VITE_APP_BASE_API`/`VITE_APP_PLATFORM`

## 7. 交付规范(本用户)

- 渗透交付 = 正式报告(执行摘要/漏洞详情含复现命令/利用链/盈利分析/修复建议/证据附录), 存 `D:\渗透\<目标>_recon\` 并复制桌面
- 多阶段报告保留(中期/阶段N/最终), 最终版含完整攻击链与资金盘点
- 诚实结论优先: 能读≠能转(内账数字 vs 链上真钱), 资金盘"转不走"要讲清是结构问题
