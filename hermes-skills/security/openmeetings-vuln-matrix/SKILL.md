---
name: openmeetings-vuln-matrix
description: "Use when 打 Apache OpenMeetings：12 条未授权/IDOR/SOAP 越权/备份路径，含 stale install 抢管理员。"
---

# Apache OpenMeetings 漏洞矩阵（12 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 Apache OpenMeetings 上一次性产出 12 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `openmeetings-backup-config-path` | High | Remote | File write leftover | ADMIN_BACKUP import skips Path.of on Type.PATH |
| `openmeetings-calendar-save-idor` | High | Remote | IDOR | LOGIN calendar save overwrites appointment and closes public room |
| `openmeetings-chat-user-idor` | High | Remote | IDOR | dashboard chatTab-u{id} exports another users private chat |
| `openmeetings-cluster-openjpa` | High | Remote | CWE-502 | clustering OpenJPA RemoteCommitProvider TCP 5636 |
| `openmeetings-invite-recording-acl` | High | Remote | IDOR | Type.USER invitation recording MP4 ACL |
| `openmeetings-kms-unauth` | High | Remote | Unauth KMS | docs docker publishes Kurento JSON-RPC on 8888 |
| `openmeetings-nettest-ping-dos` | High | Remote | DoS leftover | unauth NetTest ping POST reads body to EOF |
| `openmeetings-remember-me-password` | High | Remote | ATO | remember-me cookie replay authenticates without password |
| `openmeetings-soap-otp-skip` | High | Remote | 2FA skip | SOAP/REST password login skips TOTP |
| `openmeetings-soap-user-rights` | High | Remote | Privilege leftover | SOAP POST /user copies UserDTO.rights including ADMIN |
| `openmeetings-stale-install-admin` | High | Remote | Privilege leftover | stale /install wizard inserts second ADMIN |
| `openmeetings-wb-fileid-idor` | High | Remote | IDOR | WHITEBOARD fileId plant then room file resource serves bytes |

## 逐条要点（Class/Reach 原文摘录）
### `openmeetings-backup-config-path`
  - **Class:** File write leftover
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0` (`9773c59e`) - Apache Software Foundation
### `openmeetings-calendar-save-idor`
  - **Class:** IDOR
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0` (`9773c59e`) - Apache Software Foundation
### `openmeetings-chat-user-idor`
  - **Class:** IDOR
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0` (`9773c59e`). Any ROOM/DASHBOARD session exports another user's private chat by setting `activeTab=chatTab-u{id}`. `ChatToolbar` user branch is `u -> true`. Save/delete
### `openmeetings-cluster-openjpa`
  - **Class:** CWE-502
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. Leftover of [CVE-2024-54676](https://www.cve.org/CVERecord?id=CVE-2024-54676) (docs whitelist). Default `bin/startup.sh` does not set OpenJPA lists. Clustering.xml / s
### `openmeetings-invite-recording-acl`
  - **Class:** IDOR
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. [CVE-2023-29032](https://www.cve.org/CVERecord?id=CVE-2023-29032) stopped copying Wicket ADMIN into `WebSession.rights`. `checkHashes` still `setUser(invitation.getInv
### `openmeetings-kms-unauth`
  - **Class:** Unauth KMS
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0` (`9773c59e`) - Apache Software Foundation
### `openmeetings-nettest-ping-dos`
  - **Class:** DoS leftover
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. Leftover of [CVE-2021-27576](https://www.cve.org/CVERecord?id=CVE-2021-27576). `RateLimitRequestFilter` returns early for `type=ping` and `type=jitter` (no 3s delay, n
### `openmeetings-remember-me-password`
  - **Class:** ATO
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. [CVE-2026-33266](https://www.cve.org/CVERecord?id=CVE-2026-33266) closed the hardcoded remember-me key (per-instance AES-GCM). Cookie `LoggedIn` still holds username+p
### `openmeetings-soap-otp-skip`
  - **Class:** 2FA skip
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. When `otp.enabled` is true, TOTP runs only in Wicket `SignInDialog.processOtp`. `UserWebService.login` is password then `sessionDao.create`. SOAP/REST mint a SID with 
### `openmeetings-soap-user-rights`
  - **Class:** Privilege leftover
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. SOAP `POST /user/` copies `UserDTO.rights` and will update by `id`. SOAP is the LMS integration account. It is supposed to stay below ADMIN. `UserMapper` does `userDao
### `openmeetings-stale-install-admin`
  - **Class:** Privilege leftover
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0` (`9773c59e`) - Apache Software Foundation
### `openmeetings-wb-fileid-idor`
  - **Class:** IDOR
  - **Reach:** Remote
  - **Apache OpenMeetings** `9.1.0`. WHITEBOARD/PRESENTER `CREATE_OBJ` stores client JSON including any `fileId`. `RoomResourceReference` then serves those bytes if `isAtWb` sees that id. [CVE-2026-49488]

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
