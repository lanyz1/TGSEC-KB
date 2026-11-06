# 从 presigned URL 离线还原存储密钥(SigV4 签名比对)

适用:**AK 已知(`X-Amz-Credential` / `access_key_id` 已经在手),SK 未知**,但拿到了该 AK **签发的 presigned URL**。
这是 SKILL.md「AK 存在性 oracle」的**离线孪生兄弟**:那条要在线打点,这条**零流量、零限流、零告警、随时可停**,
且不受 WAF/出口封禁影响。

## 为什么成立

`X-Amz-Signature` = 对 CanonicalRequest 做 HMAC-SHA256 链(日期→region→service→aws4_request)的确定性输出。
给出**完整** presigned URL(含全部 query 参数、path、Host)后,可对任意候选 SK 复算签名并逐字节比对 ——
等于一次纯本地的口令验证。

## 步骤

1. **取完整样本**:日志里的 URL 常被截断(缺 `X-Amz-Signature`),**重跑一次签名接口**拿全量;
   顺手取 **2–3 个不同 `X-Amz-Date`** 的样本,命中后用于交叉验证(同一 SK 必须全部通过)。
2. **归一化 canonical query**:去掉 `X-Amz-Signature`,**按编码后的 key 排序**(ASCII 下大写 `X-Amz-*` 排在
   `response-*` 之前),值用 URL 里**原样的编码串**(不要重新 quote)。
3. **`X-Amz-Credential` 是 URL 编码的**:`AK%2F20260920%2Fus-west%2Fs3%2Faws4_request` ——
   **先 `unquote` 再 `split('/')`**,直接 split 会 `IndexError`(实测踩过,自校验与破解一起崩)。
4. **CanonicalRequest 形态**(presigned 固定 `UNSIGNED-PAYLOAD`):
   ```
   METHOD\n<URI 原样编码>\n<canonical_query>\nhost:<host>\n\nhost\nUNSIGNED-PAYLOAD
   ```
   注意 headers 段**自带一个尾 `\n`,再补一个空行**才接 SignedHeaders。
5. **自校验(不可跳过)**:用 botocore 生成一条**已知 SK** 的 presigned URL,断言自己的 `verify(sk, url) is True`。
   - **必须用 `botocore.auth.S3SigV4QueryAuth`,不是通用的 `SigV4QueryAuth`** ——
     通用版把 payload hash 算成**空体 sha256**(`e3b0c44298fc…`),而真实 S3/MinIO presigned 用的是
     `UNSIGNED-PAYLOAD`。

   用错类自校验必然失败,你会误以为是自己的 canonical 化写错,去改本来正确的代码。
   - 自校验也顺带证明「签名算法写错」这个假阴性来源已被排除。
6. **候选集**(全离线,几十万条几秒):
   - **厂商/品牌/项目词根**及其变异(大小写、首字母大写、`+!_@#.` 分隔、年份 `2020–2026`、`123/1234/123456/@123/@年份`)——
     AK 命名是人工取的(`WebConsoleUser1` 这种),SK 往往同族,**词根要用厂商名而不是通用密码表**;
   - 本机通用字典 + 运维惯用名(`admin/minioadmin/root/cloudreve/oss/s3/storage`);
   - 命中 AK 后**换一个必然不存在的 AK 打一发**做基线,确认端点确实会回「AK 不存在」。
7. **命中后**:立刻在其它样本上交叉验证 → 用官方 SDK `list_buckets()` 做**真访问**验证 → 报告里凭据
   [REDACTED](只写存在性与能力)。

## 判据与止损

- **只有自校验通过之后的「未命中」才是可信负结论**;没通过自校验就宣布「密钥爆不出来」是假阴性
  (实测:自校验失败时那 18 万候选的结果一文不值,修好后重跑才有意义)。
- **真未命中就别再加大字典**:随机 40 字符 base64 不可字典化。转去找「能读服务端文件/配置/内存」的原语:
  同机的 Loki `/config`(常把 key **掩码成 `********`**)、Prometheus scrape 配置里的 `basic_auth`、
  容器 env、CI 变量;注意 **pprof heap 是分配栈、不含字符串字面量**,拿它掘密钥是无效功(实测)。
- 旁证有用:Loki `storage_config.s3` 里 `access_key_id` 明文而 `secret_access_key` 掩码 = 说明应用服务端
  持有明文 ⇒ **下一步该找的是「能读应用配置」的原语,不是更大的字典**。

## 交付物

- `crack_sigv4.py` —— 归一化 + 自校验 + 字典/变异候选 + 交叉验证,一次跑完打印 `HIT/NOHIT`
- 结论写法:`自校验通过(SK=已知值往返验证) ⇒ 候选集 N 条未命中,判定 SK 为随机强口令,字典路终止`
