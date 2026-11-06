# 同 IP 多 vhost：从业务站挖到供应商运维栈

## 0. 为什么先做这一步

规模化运营体（账号工厂/发卡/接码/白标/代付）几乎都是「一台机顶全栈」：产品站 + 后台 + 代码仓库 + 镜像仓库 + 日志库 + 监控 + 对象存储，全挂在同一 IP 的 443 上靠 nginx vhost 分流。安全组只放 80/443（其余 65525 端口 filtered）时，**vhost 是唯一入口**。

## 1. 先把入口标定清楚

```bash
dig +short target.com
# 无 SNI 时返回什么证书（默认证书常暴露同机其它域名）
openssl s_client -connect <IP>:443 -servername target.com </dev/null 2>/dev/null \
  | openssl x509 -noout -text | grep -A2 'Subject Alternative Name'
# 证书 SAN 里那一串域名 = 第一批候选 vhost
curl -sk https://<IP>/ -H 'Host: <候选>' -o /dev/null -w '%{http_code} %{size_download}\n'
```

## 2. 词表：英文 5000 + 中文拼音 470（重点在这）

- 英文块用 `assetnote/commonspeak2` 或 `subdomains-top1million`，**只取标签级**（第一段），别用整域词表。
- ★ **拼音/缩写块（中文团队自建服务的真实命名）**：
  ```
  gongju(工具) jiankong(监控) rizhi(日志) daima(代码) cangku(仓库) yun(云) guanli(管理)
  houtai(后台) zhichi(支持) kefu(客服) zhangwu(账务) dingdan(订单) zhifu(支付) tongji(统计)
  shuju(数据) xitong(系统) yingyong(应用) neiwang(内网) ceshi(测试) shangjia(商家)
  git svn hub es kb kibana up oss s3 ip tools ops dev test stage uat admin panel
  monitor log sql db redis mq nacos k8s cdn api gw sso mail push sms
  ```
- 域名后缀要**铺全组织所有域**（`target.com` / `target.top` / `target.cc` / 兄弟商标域）。运维栈常挂在看起来「不相干」的第二个后缀上（实测形态：`git.<org>.top` / `es.<org>.top`，与主站 `.com` 完全不同）。
- 只跑英文会**整块漏掉**中文团队自建服务——这是最常犯的错。

## 3. 判据：先标定机器类型，再枚举（否则全是假阳性）

| 机器类型 | 未知 Host 的表现 | 判据 |
|---|---|---|
| 常量兜底型 | 统一 `403/404` + 固定长度 | 只有**偏离常量**的才算命中（catch-all 基线法） |
| `return 444` 型 | 空响应、连接被关（curl RC 52） | **任何有响应的 Host 都是真 vhost**，信噪比极高 |

- 标定：跑一个已知真 vhost（目标主域）+ 一个编造随机 Host，看两者是否同响 → 决定用哪种判据。
- 泛域名证书（`*.vendor.top`）时 CT/crt.sh 只剩一条基名 ⇒ **被动面全盲，只能爆破**；不要把「CT 上没有」写成「不存在」。
- 完整判据复用 `recon-discriminators/references/vhost-and-oracle-discriminators.md` §1.1–1.4（444 型识别、405 自述、301/307 后端口、泛域名盲区）。
- 每个新 vhost 先打 **GET/HEAD/POST/PUT/OPTIONS/PATCH/DELETE 七种方法**各一发并读 body 片段 —— 405 文案常直接自述后端是什么（例：`Only PUT/POST/OPTIONS are permitted on upload.<域名>`）。

## 4. 命中之后：落表、定型、分流

- 每条命中记四元组并落 CSV：`Host | 状态码 | 字节数 | <title>`。**别用眼睛扫**，N 个候选靠聚合才看得清。
- 名字只是**预期**，定型必须靠响应（`Server` 头 / 专属端点 / 错误体文案）：`es.` 回 401 + `security_exception` 才是 Elasticsearch；回 200 要看清是不是别的服务。
- 出现 **git / hub / es / kb / up / oss / ip** 这一组名字 ⇒ 你打到的是**运维栈**。此时**停止打业务站**，按服务逐门推进：`vendor-infra-service-matrix.md`。

## 5. 反模式

- 用整域词表跑 Host 头枚举（噪音大、浪费配额）。
- 只跑英文词表。
- 命中一个就开打、不落 CSV ⇒ 报告里无法对账「发现 N 个 vhost」，也看不出 catch-all 兜底。
