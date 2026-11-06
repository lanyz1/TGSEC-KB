<!-- archived from /root/.hermes/skills/security/credential-hunter-v6/SKILL.md on 2026-10-21 -->

---
name: credential-hunter-v6
description: "全自动凭证猎取与 JVM HeapDump 内存淘金（七重流水线）"
---

> 归档卡：原目录 `/root/.hermes/skills/security/credential-hunter-v6`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/credential-hunter-v6/…')`，不要相对 `references/legacy/` 解析。

# Credential Hunter v6 · 猎杀者 (韩立攻伐大成版)

全自动凭证猎取法器：六引擎(FOFA/Shodan/Censys/Quake)联合搜索 × 50+ AI工具目录 × 30+ CVE/未授权爆破点 × JDumpSpider JVM堆转魂解 × 真火验伪。

## 触发场景
- 需要对一批资产/网段做全自动凭证与密钥猎取
- 目标暴露目录列表 / AI工具配置目录(.claude/.codex/.cursor/.gemini/.n8n/.dify等)
- 目标含 Spring Boot Actuator / HeapDump / Nacos / MinIO / Jenkins / Metabase

## 七重攻伐大阵
- Step 0 猎场建立：mkdir -p hunt/{csv,auths,ssh_keys,env_files,configs,db_files,js_files,logs,backups,k8s,terraform,ci_cd,screenshots,heapdump,jdumpspider,cve_findings,shiro_keys,nacos_config}
- Step 1 识海搜天：FOFA qbase64 搜索 AI工具目录 + CVE指纹 + Shodan/Censys/Quake 辅助
- Step 2 天眼融合：解析各引擎 JSON 结果去重 → /tmp/unique_urls.txt
- Step 3 千魂破禁：xargs -P 100 并行存活检测 + 指纹打标(AI工具/CVE/Dump/Shiro/Actuator/DotEnv)
- Step 4-11 魔器提炼：提取 .claude/.codex/.cursor/.n8n/.dify 等 50+ 工具配置里的 AI Key
- Step 12 CVE淘金：Actuator env + HeapDump下载(限50MB) + Nacos未授权(CVE-2021-29441) + MinIO(CVE-2023-28432) + Jenkins
- Step 13 全局Key抽取：正则匹配 openai/anthropic/deepseek/google/groq/replicate/huggingface key
- Step 13b 堆转魂解：JDumpSpider.jar(Java) 或 Pure-Python HPROF 降级引擎，提取 DataSource URL/OSS AK(LTAI/AKID)/Shiro key/密码
- Step 14 真火验伪：并发验证 OpenAI(/v1/models) 与 DeepSeek(/user/balance) Key 死活与额度
- Step 15 天道归宗：HTML/JSON/MD 报告 + Webhook 推送

## 关键配置
- FOFA API: https://fofoapi.com/api/v1/search/all?key=$FOFA_KEY&qbase64=$QB64&size=1000
- 引擎 key: FOFA_KEY / SHODAN_KEY / CENSYS_KEY / QUAKE_KEY / WEBHOOK_URL
- JDumpSpider jar: /var/minis/attachments/uploads/JDumpSpider-1.1-SNAPSHOT-full.jar
- Java 不可用时自动降级 Pure-Python HPROF 二进制提取引擎（latin1 解码 + 正则淘金）

## 常用 FOFA CVE 语法
- Spring Boot Actuator: body="heapdump" / body="/actuator/env" / title="Directory listing for /" && body="heapdump"
- Nacos: title="Nacos" || body="nacos/v1/cs/configs" / body="/nacos/v1/auth/users"
- MinIO(CVE-2023-28432): body="minio" && body="MINIO_ROOT_USER"
- Jenkins: title="Dashboard [Jenkins]" || body="Jenkins-Version"
- Metabase(CVE-2023-38646): body="metabase" && body="setup-token"
- Docker/Kubelet: port="2375" && body="Docker" / port="10250" && body="Unauthorized"
- Ray: title="Ray Dashboard" || port="8265"

## 完整流水线脚本
见 references/credential-hunter-v6.md（原文，含完整 bash/python 可执行命令）
