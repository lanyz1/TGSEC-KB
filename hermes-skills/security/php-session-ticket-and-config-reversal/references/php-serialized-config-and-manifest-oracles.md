# PHP 序列化配置 · 缓存重建 · .git/index 清单 oracle

配套 `php-session-ticket-and-config-reversal` SKILL.md §3 / §5 的细节与命令。

## 1. 缓存重建模式：配置行 → 缓存键

中式 PHP 系统的通行形状：

```
配置表(每行一个键)  --重建-->  缓存表某键(整个配置的 PHP 序列化串)
                                        ↑
                                    全站读这里
```

**判据**：站点名/密钥/开关这类值，在原始配置表里是分散的行，在缓存键里是一个长串。
凡是「代码里 grep 不到该值、但页面行为受它控制」的字段，都要去缓存键里找。

- 缓存键的值可能被**截断**存储 ⇒ 解析前先确认串完整（结构闭合）
- 缓存通常有**过期重建**机制 ⇒ 改原始配置行后不一定立刻生效，
  别用「改了没变」推断「该配置不生效」

## 2. 序列化串解析：成对抓，别按分隔符切

```python
import re

PAIR = re.compile(r's:(\d+):"((?:[^"\\]|\\.)*)";')

def kv(serialized: str):
    out, pos = [], 0
    while True:
        m = PAIR.search(serialized, pos)
        if not m:
            break
        key = m.group(2)
        pos = m.end()
        m2 = PAIR.search(serialized, pos)
        if not m2:
            break
        out.append((key, m2.group(2)))
        pos = m2.end()
    return out
```

**为什么必须成对**：序列化串里键和值都是 `s:N:"…";` 形式，
按 `:` / `;` 裸切会在 `";s:` 边界错位，**静默丢字段** —— 丢的恰好可能是口令/密钥字段，
而所有后续推导都会基于错值（不报错，只一路推错）。

**自检**：数键数并与预期规模对比。键数明显偏少 = 解析器问题，不是配置缺项。

其他形态：

| 形态 | 处理 |
|---|---|
| `a:N:{…}` 数组 | 先剥 `a:N:` 再迭代；嵌套要递归 |
| `s:N:"…";` 二进制安全 | 长度 N 是**字节数**，中文/`\0` 不能按字符数切 |
| 值里含转义引号 | 用上面 `(?:[^"\\]|\\.)*` 而不是 `[^"]*` |
| JSON 而非 PHP 序列化 | 直接 `json.loads`；混合串先定位 JSON 子串 |

## 3. 值得单独捞的键类别

| 类别 | 用途 |
|---|---|
| 票 / 接口密钥 | 解密 cookie 票（SKILL.md §1）|
| 定时任务密钥 | 打任务/回调面 |
| RSA 公私钥对 | 伪造签名、解密前端加密参数 |
| 口令字段 | 本地离线验证（SKILL.md §7）|
| 验证码开关 / id / key | 判「在线 vs 离线校验」——离线模式可直接绕过 |
| 注册开关 / 注册价格 / 注册 uid | 判能否自建可控账号 |
| 结算 / 代付配置 | 资金面 |
| 第三方通道凭据（短信/推送/打印/邮件）| 横向 |

## 4. `.git/index` 做文件清单 oracle

`objects/` 被 deny 时仍可读 `.git/index`，它含**全量被跟踪文件路径 + 每个 blob 的 SHA1**。

做法 A — 驱动静态资源收割（枚举所有可达非 PHP 文件）：

```python
# index 结构: 12 字节头 + 每条 62 字节定长项 + 变长(路径) + NUL + padding
# 只要路径时, 直接从二进制里扫可打印路径段更快:
import re
blob = open(".git/index", "rb").read()
paths = re.findall(rb"[\x20-\x7e]{4,}", blob)
```

做法 B — 找出「线上独有的二开产物」（**价值最高**）：

```bash
# 线上: 已解析出的 (path -> blob_sha1) 落成 online_index.tsv
# 本地同名项目:
git -C D:/path/to/fork ls-files -s > local_index.tsv
# 每行形如: <mode> <sha1> <stage>\t<path>
# 逐路径比对 sha1:
#   相同  -> 与 fork 同版
#   不同  -> 二开改过
#   本地无 -> 线上独有 (重点读)
```

做法 C — 拿分支名 + commit 链找上游：`.git/packed-refs` 与 `.git/FETCH_HEAD`
给分支名与 commit 链，去代码托管站搜同源仓，或本地 fork `git fetch` 试取。

⚠️ 二开仓常私有 ⇒ 上游 404 / 本地 fetch 取不到 / blob 全 `NOT_IN_LOCAL` 是**常态**。
三条都死立刻停手转线上面，不要换仓库来回试。

## 5. 静态资源收割的执行纪律

- **增量落盘**：每批结果 `append` 进 JSONL，跑完再汇总 ⇒ 中途超时/中断不丢进度
- **候选数要压住**：`execute_code` 里一次打完整清单（含 vendor/资源目录）会超时
  ⇒ 写后台脚本、只打高价值前缀、跳过已知 deny 前缀
- **字段名统一**：落盘记录用固定键（如 `path` / `status` / `bytes`），后续汇总脚本按同一键读 ——
  中途改键名会让汇总脚本 `KeyError` 直接崩掉整轮产物
- 只看 `200` 且**体积异常**的（模板、json、部署配置、备份、日志）；
  体积接近全站首页的通常是 SPA 回退页，不是真资源
