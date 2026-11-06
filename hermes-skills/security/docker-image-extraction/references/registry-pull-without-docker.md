# Registry API 拉镜像 — 完整流程(无 docker 客户端)

2026-08 QQLink/wallet8 实战验证。跳板机无 docker、深圳出口访问 hub.docker.com 超时;本机经 v2rayN `socks5h://127.0.0.1:10808` 直连 Docker Hub 成功。

## 1. 查 Docker Hub tag 列表(找可用版本)

```python
import requests, json
PROXY = {"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}
r = requests.get("https://hub.docker.com/v2/repositories/asdmd007/wallet/tags?page_size=100", proxies=PROXY, timeout=30)
# r.json()["results"][i]["name"] -> tag 列表; "last_updated" 可排序
```

注意:Hub 最新版 ≠ 生产版(案例:生产 registry 用 v1.0.548,Hub 最新 v1.0.534)。逻辑结构一致即可用。

## 2. token

```python
r = requests.get("https://auth.docker.io/token?service=registry.docker.io&scope=repository:asdmd007/wallet:pull", proxies=PROXY, timeout=30)
token = <REDACTED>"token"]
```

## 3. manifest(⚠ 可能是 OCI index)

```python
HDR = {"Authorization": f"Bearer {token}",
       "Accept": "application/vnd.docker.distribution.manifest.v2+json"}
r = requests.get("https://registry-1.docker.io/v2/asdmd007/wallet/manifests/v1.0.534", headers=HDR, proxies=PROXY, timeout=60)
m = r.json()
if m.get("mediaType") == "application/vnd.oci.image.index.v1+json":
    # 多平台:选 linux/amd64
    amd = [x for x in m["manifests"] if x["platform"]["architecture"] == "amd64"][0]
    r2 = requests.get("https://registry-1.docker.io/v2/asdmd007/wallet/manifests/" + amd["digest"], headers=HDR, proxies=PROXY, timeout=60)
    m = r2.json()
layers = [l["digest"] for l in m["layers"]]  # sha256:...
```

关键坑:manifest 直接返回时 mediaType 是 `application/vnd.docker.distribution.manifest.v2+json` 才有 `layers`;OCI index 的 `manifests[]` 是平台列表,**没有 layers**,必须再取一次子 manifest。

## 4. 拉层 + 校验

```python
for i, d in enumerate(layers):
    r = requests.get(f"https://registry-1.docker.io/v2/asdmd007/wallet/blobs/{d}", headers=HDR, proxies=PROXY, timeout=600, stream=True)
    out = f"layer_{i}.tar.gz"
    with open(out, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
# 校验:sha256sum layer_N.tar.gz == digest 去掉 sha256: 前缀
```

## 5. 解包(必须关过滤)

```python
import tarfile
tf = tarfile.open("layer_3.tar.gz")
tf.extractall("rootfs", filter=None)   # filter=None 关键!镜像含绝对路径软链接
```

Python 3.12+ 默认 filter='data',遇 `link name is absolute`(镜像内 /app、/usr 软链)直接抛错。本地分析信任,必须 None。

## 6. 找产物

- Go 服务端镜像:常为 `/app/main` 单二进制(GoFrame/gin),52MB 级。
- 也找 `.env`、`config.yaml`、`*.pem`(RSA 私钥)、`docker-compose.yml`(揭示服务编排、其他镜像名、端口映射)。

## 私有 registry 域名挖掘

- App 二进制/配置里的 config.txt 常有域名映射(案例:`qqlink.top,wallet8.cc` / `qqlink.im,wallet8.im`)→ 从映射域名试 `registry.<domain>`。
- 注意:registry 域名可能不是真 registry(案例:`registry.wallet8.im` 实际是 GVA 管理后台前端,不是 Docker Registry;其前端 JS 暴露了真实 API baseURL)。
