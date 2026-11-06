# XCard / bitcoinscard OSS 桶侦察（2026-10-19）

Context: `bitcoinscard.org` -> XCard (`xcardweb.com`, `x-card.co`). 桶名来自 JS/OSS 命名猜测（品牌 + `-dev`/`-card`），不是 APK 泄露。

## Buckets

| Bucket | Endpoint / region | List | Random object | Verdict |
|---|---|---|---|---|
| `xcard` | cn-hangzhou | 403 anonymous | `NoSuchKey` | object-public；确定性 key 全空 |
| `x-card` | cn-shenzhen | 403 | `NoSuchKey` | object-public |
| `mos` | cn-hangzhou | 403 | `NoSuchKey` | object-public |
| `xcard-card` | 先 cn-beijing -> `oss-ap-southeast-1` | 403 | `NoSuchKey` | object-public；region mismatch |
| `xcard-dev` | cn-shanghai | 403 | `NoSuchKey` | object-public；dev 桶，已知 key 为空 |
| `xcapp` | - | 403 | 403 object | private |
| `mos-app` | - | 403 | 403 object | private |

没有命中 `xcard-backup` / `mos-backup`；没有任何对象被读出。

## Keys tried

`backup.sql`、`db.sql`、`config.json`、`.env`、`users.csv`、`xcard.apk`、`apk/xcard.apk`、`bin/49372408.png`、日期式 `xcard_YYYYMMDD.sql`、`sql/...`、`backup/...` —— 全部 `NoSuchKey`。

## Lessons

- `xcard-dev` / `xcard-card` 暴露命名规律：品牌 + 环境/产品后缀。**object-public 但对象为空是死端，不是泄露**。
- `xcard-card` 先对 cn-beijing 回 `must be addressed using the specified endpoint`；从 XML 取 `<Endpoint>`（`oss-ap-southeast-1.aliyuncs.com`）再测，不能因最初 403 判私有。
- 报告只能写“桶存在 + 对象公开/List 403，未读到对象”；不要写成“7 个 OSS 桶被拿下”。
- 若应用有上传/STS 接口，优先 pivot 到签名凭证；确定性备份 key 在这类品牌桶里通常不存在。
