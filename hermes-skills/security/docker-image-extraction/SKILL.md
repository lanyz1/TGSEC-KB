---
name: docker-image-extraction
description: 拉镜像/registry API/OCI manifest/镜像解包, 无 docker 客户端提取服务端二进制逆向。
---

# Docker Image Extraction(镜像拉取与分析)

跳板机无 docker、hub 被墙、或目标用私有 registry 时,直接用 registry HTTP API 拉镜像并解包,提取服务端二进制/配置做本地逆向。**这是拿"平台服务端代码"的标准路径**:镜像名从 compose 文件、案卷配置、或 App 字符串里挖。

## 一、完整流程

1. **找镜像名**:目标平台的 docker-compose / 案卷 / 报告里常有 `registry.xxx.top/wallet:v1.0.548` 或 Docker Hub 用户名如 `asdmd007/wallet`。Docker Hub 上的公开镜像可先查 tag 列表:
   `https://hub.docker.com/v2/repositories/<owner>/<repo>/tags?page_size=100`(返回 JSON,含 tag 名+更新时间)
2. **token**(仅 Docker Hub 需要):
   `https://auth.docker.io/token?service=registry.docker.io&scope=repository:<repo>:pull`
3. **manifest**:
   `https://registry-1.docker.io/v2/<repo>/manifests/<tag>`,请求头 `Accept: application/vnd.docker.distribution.manifest.v2+json`
4. **⚠ OCI index 多平台**:manifest 可能返回 `mediaType: application/vnd.oci.image.index.v1+json`,layers 在 `manifests[]` 里按 platform 分。选 `linux/amd64` 的 digest 再取子 manifest 才拿到 layers。
5. **拉层**:`https://registry-1.docker.io/v2/<repo>/blobs/sha256:<digest>`,存盘后 `sha256sum` 验证 digest。
6. **解包**:`tarfile.open(f, filter=None)`——镜像层含绝对路径软链接,Python 默认安全过滤器直接拒绝("link name is absolute")。本地分析信任,必须关过滤。
7. **找产物**:Go 服务端常是 `/app/main` 单二进制(GoFrame/gin 等);也找 `.env`、`config.yaml`、`*.pem`、`docker-compose.yml`。

## 二、代理与网络

- 跳板机访问 hub.docker.com 超时 ≠ 镜像不存在。本机经 v2rayN `socks5h://127.0.0.1:10808` 拉 Docker Hub 公开镜像可行(第三方基础设施,非目标网络,无 IP 暴露风险)。
- 私有 registry 域名不解析时,从目标 App 的 config.txt/域名映射里挖备用域名(如 qqlink.top ↔ wallet8.cc)。

## 三、后续逆向

- Go 二进制 → 见 `golang-reverse` 技能(pclntab 解析函数表,注意 Go 1.24+ 的 _func 是 **48 字节**不是 40,用 40 会函数名丢前缀)。
- 常见目标:配置 key 字符串(`xxx.aeskey`)、加密函数(`gaes.EncryptCBC`)、上传/校验接口实现。

## 四、配套文件
- references/registry-pull-without-docker.md —— 完整 Python 拉取代码与格式细节
- references/wallet8-qqlink-case.md —— QQLink/wallet8 实战案例(含 Go 1.24+ pclntab 48 字节坑的完整调试过程)
