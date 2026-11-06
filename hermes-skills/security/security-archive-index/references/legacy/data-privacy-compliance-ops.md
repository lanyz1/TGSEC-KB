<!-- archived from /root/.hermes/skills/security/data-privacy-compliance-ops/SKILL.md on 2026-10-21 -->

---
name: data-privacy-compliance-ops
description: "Use when 数据安全/隐私/合规映射:DLP、脱敏、等保、CVSS优先级。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/data-privacy-compliance-ops`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/data-privacy-compliance-ops/…')`，不要相对 `references/legacy/` 解析。

# 数据安全与合规交付（渗透/众测视角）

面向授权测试交付：客户在报告里要合规影响、要等保/个保法口径，或要真的去测"数据面"（分类分级、DLP、脱敏、加密、备份）。不做治理叙事，只给能落到报告和命令行里的东西。

## 触发场景

- 客户问"这个漏洞触犯哪条合规要求？" / 报告"合规影响"栏写不出来
- 要出等保 2.0 三级自查/差距分析清单，或要对着等保控制项做核查
- 要跨框架映射：等保 ↔ ISO 27001:2022 ↔ NIST CSF 2.0 ↔ SOC 2 ↔ PCI DSS 4.0 ↔ GDPR/个保法
- 数据面测试：脱敏是不是真的有效、DLP 能不能绕过、数据库/备份有没有加密
- 要出 CVSS v3.1/v4.0 + EPSS 的修复排序与 SLA，而不是只丢一堆 CVSS 分
- 客户拿生产数据/备份给测试环境，要评"这算不算泄露风险"
- 个保法/ GDPR 流程类问题：ROPA、DSAR、跨境、PIA/DPIA、泄露通知

## 工作流

1. **定范围与角色**：先问清是"合规核查"还是"渗透中发现"。是渗透 → 每个发现只做合规映射，不替客户做合规结论；是核查 → 走 §2。
2. **拿数据清单**：索取数据资产/分类分级表。没有清单本身就是一个发现（最小权限无从证明，等保访问控制 + 个保法最小必要同时不满足）。
3. **对照两套尺子**：等保控制项名称（技术 5 类 + 管理 5 类）→ 映射表（见 compliance-frameworks-cn.md §2）→ 法规锚点。
4. **数据面实测**（顺序别反，先看数据再打通道）：
   - 分级与标签：高敏列有没有标识、有没有加密/掩码；
   - 取数路径：直连库 / API / 导出 / 从库备份 / 日志 —— 同一 PII 走 5 条路，任一回明文即"脱敏无效"；
   - 掩码旁路：掩码列能否 `WHERE`/`ORDER BY`/`COUNT(DISTINCT)` 推断，DDM 能否被导出绕过；
   - 外传通道：编码/压缩/加密压缩/分片/TLS/云盘直传/剪贴板（见 §DLP 绕过）；
   - 备份：是否加密、密钥在哪、恢复到测试环境后是否仍是脱敏数据。
5. **定级与排序**：CVSS（写明 v3.1 还是 v4.0）+ EPSS + 资产权重 → P0–P4 与建议 SLA。
6. **写报告**：发现 → 影响 → 合规映射（等保控制项名 + 框架条款 + 法律）→ 修复 → 验证方法。条款号一律写标准全名 + 版本 +「需核对现行文本」。

## 命令速查

```bash
# —— 等保/主机基线核查 ——
grep -E '^(PASS_MAX_DAYS|PASS_MIN_LEN|UMASK)' /etc/login.defs
ss -tlnp; find / -perm -4000 -type f 2>/dev/null
auditpol /get /category:*            # Windows 审计策略
psql -c "SHOW ssl;"; mysql -e "SELECT User,Host FROM mysql.user WHERE User='';"
lynis audit system --quick

# —— DLP/数据发现（存储面）——
rg -a -n -u --hidden -e '1[3-9]\d{9}' -e '\b(?:\d[ -]?){13,16}\b' /mnt/share
gitleaks detect --source /data --no-git -v
trufflehog filesystem /data --only-verified --json
aws macie2 create-classification-job --job-type ONE_TIME --name pii-scan \
  --s3-job-definition '{"bucketDefinitions":[{"accountId":"123456789012","buckets":["my-bucket"]}]}'

# —— 网络面 ——
zeek -C -r capture.pcap; zeek-cut uri host < http.log | grep -iE 'upload|export'
export SSLKEYLOGFILE=$TMPDIR/keys.log    # TLS 后内容要能看见，必须先落 keylog
tshark -o tls.keylog_file:$TMPDIR/keys.log -r capture.pcap -Y http2

# —— DLP 绕过验证 ——
echo -n <PHONE-REDACTED> | base64                       # 编码外传
7z a -pPASS -mhe=on out.7z data.csv                # 加密压缩（连文件名一起加密）
steghide embed -cf cover.jpg -ef secret.txt -p p    # 隐写载体
curl --doh-url https://1.1.1.1/dns-query https://x  # 绕过域名/SNI 策略

# —— 数据库加密/掩码 ——
# SQL Server: CREATE DATABASE ENCRYPTION KEY ... ENCRYPTION BY SERVER CERTIFICATE; ALTER DATABASE ... SET ENCRYPTION ON;
# PostgreSQL: CREATE EXTENSION pgcrypto; pgp_sym_encrypt / pgp_pub_encrypt + dearmor(pg_read_binary_file(...))
# 动态脱敏(PG): CREATE EXTENSION anon CASCADE; SECURITY LABEL FOR anon ON COLUMN ...
#              IS 'MASKED WITH FUNCTION anon.partial(phone,2,$$******$$,2)'; SELECT anon.k_anonymity('t','{qi}');

# —— 备份加密 ——
mysqldump --single-transaction --routines --triggers --all-databases | gpg -e -r dba@corp > all.sql.gpg
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in dump.sql -out dump.sql.enc -pass file:/etc/backup.key
find / -xdev \( -name '*.sql' -o -name '*.dump' -o -name '*.bak' \) -size +1M 2>/dev/null

# —— 优先级 ——
curl -s "https://api.first.org/data/v1/epss?cve=CVE-2023-44487" | jq '.data[0]|{cve,epss,percentile}'
pip install cvss   # from cvss import CVSS3, CVSS4
```

## 关键判断（别踩的坑）

- **加密 ≠ 合规**：TDE 对 DBA 透明（`SELECT` 仍明文），密钥与数据同机/同仓库时只防介质丢失。判"已加密"前先问密钥在哪、谁能读。
- **脱敏 ≠ 匿名化**：去标识化数据仍属个人信息、仍可重标识。客户说"给的是脱敏数据"时要追问是否可逆。
- **掩码只挡显示**：DDM/动态脱敏不保护备份、导出、`SELECT INTO`、BULK；比较/排序/聚合仍按真值 —— 这三条是必测项。
- **网络 DLP 看不见 TLS**；终端 DLP 覆盖不全（剪贴板/截屏/打印常缺）；存储 DLP 依赖标签体系。三者都是"假设"，测试就是逐个证伪。
- **k-匿名不是万能**：同质攻击下 k 再大也泄露，高维稀疏数据做 k-匿名等于可用性归零；ε 预算是差分隐私最常翻车的点（串行组合直接相加）。
- **条款号是最易错的地方**：网络安全法 2025 年修订（2026-01-01 施行）条文序号后移，老资料里的编号已失效；等保控制点编号 `8.x.y.z` 随级别/扩展要求变化 —— 报告里宁可写控制项**名称**。
- **CVSS 高 ≠ 优先修**：必须叠加 EPSS/KEV/暴露面；反之拿 PII 的低分漏洞常被漏掉。报告里写明 CVSS 版本（v3.1 与 v4.0 分数不同）。
- 上游卡里的错误写法不要照抄：`aws macie2 … bucketId=`、pgcrypto `gen_keypair()`、`pg_ddm` 的 `CREATE MASKING POLICY`、Purview/AIP 哈希表配置、`security-audit` 工具 —— 都是不存在或语法错误，已在本 skill 的参考文件里逐条标注。

## 参考文件

- `references/data-security-dlp.md` — 分类分级体系与检查表、DLP 三形态命令、DLP 绕过检测点、数据库加密、静态/动态脱敏、k-匿名与差分隐私、备份加密与恢复演练（含上游错误命令的更正标注）
- `references/compliance-frameworks-cn.md` — 等保 2.0 测评流程与勾选清单、跨框架映射表、渗透发现的合规映射、GDPR/个保法流程（ROPA/DSAR/跨境/PIA）与模板骨架、CVSS+EPSS 优先级与 SLA
- `references/provenance-and-unverified.md`：来源核对（哪些命令搬自上游 / 哪些是补充 / 未验证清单）。
