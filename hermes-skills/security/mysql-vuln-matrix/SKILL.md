---
name: mysql-vuln-matrix
description: "Use when 打 MySQL 8.x/9.x 运维面：6 条 mysqldump 路径、binlog 路径、DEFINER SQLi、组件安装。"
---

# MySQL 漏洞矩阵（6 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 MySQL 上一次性产出 6 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `mysql-install-component-scheme` | High | INSTALL COMPONENT qualified scheme | plugin_dir skip |  |
| `mysql-jdv-definer-sqli` | High | JSON Duality DEFINER SQLi | NO_BACKSLASH_ESCAPES |  |
| `mysql-mysqlbinlog-raw-path` | High | mysqlbinlog --raw Rotate path leftover | client file write |  |
| `mysql-mysqldump-show-tables-overflow` | High | mysqldump SHOW TABLES stack overflow | crash dump UID |  |
| `mysql-mysqldump-tab-path` | High | mysqldump --tab path leftover | client file write |  |
| `mysql-set-role-leftover` | High | SET ROLE ALL EXCEPT leftover FILE | mysqld UID write |  |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
