# 攻击者工具指纹字典（溯源第一步）

判据优先级：**专用请求头 > 默认 UA 串 > 请求 URI 模式 > 时序/体积行为**。
UA 可改，单独用 UA 定案 = 误报来源；至少两条弱特征同源才算 L2。

## 强特征（工具专用头/串）

| 工具 | 特征 | 位置 |
|------|------|------|
| AWVS / Acunetix | `Acunetix-Product: WVS/x.y`、`Acunetix-Scanning-agreement`、`Acunetix-Aspect`、`Acunetix-Aspect-Password` | 请求头 |
| sqlmap | `User-Agent: sqlmap/1.x#stable (https://sqlmap.org)` | 请求头 |
| AntSword | UA 串含 `antSword`（可在设置里改） | 请求头 |
| nuclei | UA 串含 `nuclei` | 请求头 |
| xray / afrog | UA 或路径含工具名 | 请求头/URI |
| Cobalt Strike beacon | 默认 profile 的 C2 URI：`/activity` `/submit.php` `/pixel` `/updates` `/visit.php`；404 页含 checksum8 特征 | URI/响应 |
| masscan / zmap | 无 UA、无 Accept、`HTTP/1.0`、无连接复用（短时大量连接） | 全报文 |

## 弱特征（需两条以上）

| 工具 | 特征 |
|------|------|
| 冰蝎 Behinder | UA 常见 `Chrome/83-84` 段；POST 单参数且 body 为 base64/AES 密文；响应 `Content-Length` 很短；AES 密钥 = 连接密码 MD5 前 16 位 |
| 哥斯拉 Godzilla | Cookie 值末尾带分号；首包明显大于后续包；响应体固定 16+32+16 结构（md5 前后各 16 位包裹 base64） |
| 蚁剑 AntSword | 默认 UA + POST 参数含 `@ini_set`/`display_errors` 类 PHP 配置；编码器为 base64/rot13/chr 变体 |
| 菜刀 Chopper | 旧 IE UA（`MSIE 6.0/7.0`）+ `z0=`/`z1=` 参数 |
| Goby | UA 含 `Goby`（可改）；扫描线程固定间隔 |
| 目录扫描器 | UA 含 `dirsearch/feroxbuster/ffuf/gobuster/wfuzz` |

## 扩充方法（现场校准，勿只靠字典）

```bash
# 从 pcap 提 UA 频次，找"只出现一次却命中大量 404"的 UA
tshark -r a.pcap -Y 'http.request' -T fields -e http.user_agent | sort | uniq -c | sort -rn | head -30
# 单 IP 行为聚类：请求数、404 占比、路径熵
python3 scripts/scan_log_fingerprint.py --log access.log --top 20 --json out.json
```

新特征入库：在 `scripts/scan_log_fingerprint.py` 的 `FP` 列表追加一条（name/strength/why/ua|hdr|uri），
并把「发现现场」与「误报情况」写回本表。

## 误报提醒

- CDN/云 WAF 回源 IP、公司自有漏扫（Nessus/Greenbone）、监控拨测 UA 会误判成攻击。
- 先排除 **已在资产台账里的扫描器 IP** 再画像（`recon-discriminators` 同思路）。
