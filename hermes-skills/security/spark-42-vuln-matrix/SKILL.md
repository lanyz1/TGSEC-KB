---
name: spark-42-vuln-matrix
description: "Use when 打 Apache Spark 4.2.0 大数据面板：未授权 RPC 读文件、REST 鉴权失效、Connect/History 写文件。9 条。"
---

# Apache Spark 4.2.0 漏洞矩阵（9 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 Apache Spark 4.2.0 上一次性产出 9 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `spark-connect-archive-fragment` | High | Remote | File write | Connect archives hash-fragment dest |
| `spark-connect-copy-local` | High | Remote | File write | Connect session SET copyFromLocalToFs.allowDestLocal |
| `spark-history-store-path` | High | Remote | File write | History appStorePath unsanitized App ID |
| `spark-history-zip-symlink` | High | Remote | File read | History zip follows planted symlink |
| `spark-jdbc-serde-url` | High | Remote | JDBC URL injection | ALTER TABLE SET SERDEPROPERTIES |
| `spark-proxyuser-classpath` | High | Remote | Privilege leftover | proxy-user defaultExtraClassPath |
| `spark-python-ds-static` | High | Remote | Privilege leftover | process-global Python Data Source map |
| `spark-rest-auth-bypass` | High | Remote | Privilege leftover | standalone REST ignores spark.authenticate |
| `spark-rpc-stream-unauth` | High | Remote | File read | unauth RPC StreamRequest File join |

## 逐条要点（Class/Reach 原文摘录）
### `spark-connect-archive-fragment`
  - **Class:** File write
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
  - **Connect `archives/<file>#../<path>` unpacks and `deleteRecursively`s outside the session SparkFiles dir as the Spark UID.**
### `spark-connect-copy-local`
  - **Class:** File write (leftover of SPARK-58531; static on 4.3.0 only)
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
  - **Connect session SET then `forward_to_fs` writes driver-local files. Dest must be LocalFileSystem. Not RCE.**
### `spark-history-store-path`
  - **Class:** File write (config-gated)
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
### `spark-history-zip-symlink`
  - **Class:** File read
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
### `spark-jdbc-serde-url`
  - **Class:** JDBC URL injection
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
  - **A shared-catalog SQL user can retarget an operator-provisioned `USING jdbc` table and replay the stored database password to a host they choose.**
### `spark-proxyuser-classpath`
  - **Class:** Privilege leftover (leftover of CVE-2023-22946 / SPARK-41958)
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
  - **A Livy-style tenant can still load a staged jar inside the gateway `spark-submit` JVM. Hadoop `UserGroupInformation.doAs` does not change that Unix UID.**
### `spark-python-ds-static`
  - **Class:** Privilege leftover
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
### `spark-rest-auth-bypass`
  - **Class:** Privilege leftover
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
### `spark-rpc-stream-unauth`
  - **Class:** Privilege leftover / File read
  - **Reach:** Remote
  - **Apache Spark** `4.2.0` (`32f72996`) - Apache Software Foundation
  - **Unauthenticated `StreamRequest` `classes/../../path` reads Spark-UID files.** Unix absolute children stay under the registered dir (lab 404). `files/` is a map get (404). `receive()` / `receiveStrea

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
