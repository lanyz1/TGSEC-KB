# 情梦后门分析案

> RAR 源文件：`情梦后门的文件清单(README.md为分析报告).rar`（9MB）
> 本文件从文件清单和元数据推断内容（RAR5 格式需 unrar 7.x 解压正文）。

## 文件清单

| 文件 | 大小 | 类型 |
|------|------|------|
| `README.md` | 19KB | 分析报告主文（RAR 内，待解压） |
| `config.json` | 2.5KB | C2/挖矿配置 |
| `filter` | 3MB | 主控二进制（packed） |
| `filter_packed_upx` | 3MB | UPX 加壳版 |
| `filter_unpacked` | 8.5MB | 脱壳版 |
| `filter_unpacked_all_strings.txt` | 369KB | 脱壳后全量 strings |
| `udpclient_mipsel` | 162KB | MIPS 小端 DDoS UDP 客户端 |
| `udpclient_all_strings.txt` | 7.5KB | UDP 客户端 strings |
| `udpclient_strings.txt` | 8KB | UDP 客户端关键 strings |
| `sysbak_hidden` | 162KB | 伪装系统备份的挖矿进程 |
| `test` | 125KB | 测试二进制 |
| `xiazai.go` | 2KB | Go 编写的下载器源码 |
| `go.sh` | 3.9KB | 主启动脚本 |
| `run.sh` | 226B | 运行脚本 |
| `musl_config.mak` | 48B | musl 交叉编译配置 |
| `rootfs_mipsel_init_udpclient` | 277B | MIPS rootfs init 脚本（启动 UDP 客户端） |
| `rootfs_mipsel_profile` | 788B | MIPS rootfs profile |
| `ssh_authorized_keys` | 564B | 攻击者植入的 SSH 公钥 |
| `.bash_history` | 16.5KB | 被入侵服务器的 bash 历史 |
| `.bashrc` | 3.2KB | 被修改的 bashrc（可能含持久化） |
| `.profile` | 161B | profile 文件 |
| `.wget-hsts` | 261B | wget HSTS 缓存 |
| `cross_compile_evidence.txt` | 5.8KB | 交叉编译证据 |
| `persistence_evidence.txt` | 7.3KB | 持久化证据 |
| `telegram_c2_evidence.txt` | 375B | Telegram C2 证据 |
| `xmrig_evidence.txt` | 5.4KB | XMRig 挖矿证据 |
| `file_hashes.txt` | 1.4KB | 样本哈希 |

## 推断的攻击拓扑

```
攻击者
  ├── Telegram Bot C2 → 下发 DDoS/shell 命令
  ├── Go downloader (xiazai.go) → 拉取新组件
  ├── filter (主控) → 流量过滤/代理
  │   └── UPX 加壳 + musl 静态编译 → 跨平台
  ├── udpclient_mipsel → MIPS 架构 DDoS 执行器
  │   └── rootfs 级持久化（init 脚本）
  ├── sysbak_hidden → XMRig 挖矿（伪装系统备份进程名）
  └── 持久化
      ├── SSH 公钥植入
      ├── crontab 定时拉起
      ├── .bashrc 注入
      └── init 脚本自启
```

## 关键特征

- **C2**：Telegram Bot API（telegram_c2_evidence.txt）
- **DDoS**：UDP flood（MIPS 小端架构，面向路由器/IoT）
- **挖矿**：XMRig 门罗币（伪装 sysbak_hidden）
- **编译**：musl 静态链接 + UPX 加壳（跨平台、小体积）
- **持久化**：SSH 公钥 + crontab + init + bashrc（四重保险）
- **下载器**：Go 编写（xiazai.go），2KB 极简
