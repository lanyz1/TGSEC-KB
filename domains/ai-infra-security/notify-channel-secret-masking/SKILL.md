---
name: notify-channel-secret-masking
description: "把任务结果推到钉钉、企微、飞书、Telegram、邮件、通用 webhook 时，要判断哪些字段算凭据、回显时怎么遮、改投递地址时怎么拦住旧凭据外发，或要给投递地址做 scheme 与内网网段校验、算钉钉与飞书互为反序的 HMAC 签名、按 4096 字节与 4096 字符两套口径截断，或要给事件过滤器加去重、digest 合并与令牌桶限流时加载本卡；排查投递静默成功、消息被长度上限截断后条目消失、群里重复轰炸同样从本卡入手。"
sources: art-content, operator_experience
---

## 定位

推送渠道是扫描结论出门的最后一道闸，失灵点集中在三处：凭据顺着 URL、错误串、接口回显漏出去；投递地址被改成环回或云元数据端点；消息被平台长度上限截掉却仍被记成已送达。

## 事件与订阅

- 事件两型：`finding_created`、`finding_status_changed`。快照落 `notification_events.snapshot`，字段 `kind / finding_id / task_id / vulnclass / name / severity / summary / asset_ids / from_status / to_status`；存快照不回查 `findings`，消息要反映事发当时的级别，回查会读到事后被改成 low 的结论。
- `Filter` 六字段：`min_severity / task_ids / asset_ids / vulnclass_include / vulnclass_exclude / on_status_change`。`Match` 顺序固定：事件类型 → 级别门槛 → 任务与资产交集 → 排除词 → 包含词，排除优先。vulnclass 走 `strings.Contains` 大小写不敏感子串，不用正则——写错正则会让渠道静默失效。
- 宽容口径：`ParseFilter` 永不返回 error，畸形配置退化为零值 Filter（全命中）；`Validate` 只挂保存渠道这一条写路径。`severityRank` 未知级别为 0，`AtLeast` 用 0 挡掉未知级别；门槛拼错成 `hgih` 时 `rank>=0` 恒真，过滤器静默降级成全推，写入时的白名单校验就为拦这个。
- 去重：`FanOutPendingEvents` 在 `fanned_out` 布尔位加 `FOR UPDATE SKIP LOCKED` 上领取，一个 `(event_id, channel_id)` 只插一条 `notification_deliveries`；未命中任何渠道的事件同样置 `fanned_out`，否则每 3 秒 tick 被重扫。每轮上限 200 条事件。
- 合并：`mode=realtime` 一漏洞一消息；`mode=digest` 攒批。`DigestBatchDue` 判据是最老那条投递的年龄 ≥ 周期（默认 30 分钟），不看墙上时钟；`ClaimDigestBatch` 按 id 升序取前 N（上限 `MaxDigestBatchSize`=500），`batch_id` 取集合最小 id 且 `COALESCE` 保留，重试后仍是同一批。
- 频率闸门：每渠道一个 `notifyBucket` 令牌桶，容量=rate_per_min，按真实时间以 rate/60 每秒补充，取整前加 1e-9（0.5+0.5 得 0.9999999999 会被截成 0）。实时模式每轮取 `min(桶内, 5)`；digest 每轮只扣 1 个令牌，批次大小由 `digestTickPlan()` 固定返回 `(1, 500)`，与请求预算解耦。`rate_per_min<=0` 时本轮上限 50。`DefaultRatePerMin`：钉钉 20、企微 20、飞书 100、Telegram 20、邮件 60、通用 webhook 0。顺序是先取令牌再领行，反过来被限流挡下的行已记一次 attempts，3 次预算被纯等待耗光。
- 重试：`notifyBackoff` 1s/5s/30s，`MaxNotifyAttempts`=3，`IsPermanent` 的错误直接 failed。

## 渲染

- 六渠道三套模板：钉钉与企微用 markdown；飞书用 interactive 卡片（`lark_md` div + `header.template` 红橙黄蓝灰）；Telegram 用 `parse_mode=HTML`；邮件用内联样式 HTML（Outlook 与国内企业邮箱对 style 块支持差异大，内联是唯一通用写法）；通用 webhook 用 `text/template`。
- 净化：`markdownEscape` 走 `strings.NewReplacer` 逐字符处理反斜杠、反引号、`*`、`_`、`[`、`]`、`(`、`)`、`!`、`#`、`>`、`|`、`~` 共 13 个（反斜杠最先处理，否则会把后面补的反斜杠再转义一次）；`markdownText` = `OneLine` 折叠空白 + 转义，换行本身就能伪造列表项与引用块。`htmlEscape` 与 `telegramEscape` 只处理 `& < >`，属性值再补引号（`htmlEscapeAttr` / `telegramEscapeAttr`）。`markdownTitle` 刻意不转义：它被 markdown 正文、Telegram HTML、飞书 `plain_text`、webhook JSON、邮件主题五种语境共用，转义由各输出端自己做；共享函数里加过的 markdown 转义曾在 Telegram 里露出 `\(1\)`。
- 截断三口径：`TruncateBytes` 按字节并回退到 `utf8.RuneStart` 边界（企微 content 4096 **字节**硬上限，超长整条被拒，中文 3 字节/字）；`TruncateRunes` 按字符（Telegram text 4096 字符）；`TruncateHTML` 在字符截断后退掉尾部未闭合的 `<` 与半截实体（`&amp` 残片会让整条消息被拒收）。
- 预算常量：`maxAssetsShown`=3、`maxSummaryRunes`=120、`markdownReservedBytes`=320、`telegramReservedRunes`=160、`feishuMaxCardBytes`=24000、钉钉正文 20000 字节保护、`weComMarkdownLimit`=4096。
- 打包：`packItemCount` 按整条试装，装不下的留库下一批；`Send` 的返回值 kept 是接口契约，调用方只把前 kept 条标 sent，其余走 `DeferDeliveries` 并把 attempts 减回 1。渲染完整篇再截断会让后半截条目凭空消失，而投递历史显示全部成功。
- webhook 模板面：FuncMap 只有 `json` 与 `jsons`；上下文 `webhookTemplateData` / `webhookItem` 零导出方法（text/template 能调用导出方法，加一个等于把它开放给模板填写者）；`missingkey=zero`；渲染结果必须 `json.Valid`，否则判 Permanent；GET 不带 body；`content_type` 在 headers 之后应用。回链由 `baseURL + /function/findings/detail?id=<finding_id>` 拼出。

## 去密与脱敏

- 凭据键由渠道自己声明，不由上层猜：钉钉 `{webhook, secret}`、企微 `{webhook}`、飞书 `{webhook, secret}`、webhook `{url, headers}`、Telegram `{bot_token}`、邮件 `{password}`。目的地键：钉钉/企微/飞书 `{webhook}`、webhook `{url}`、Telegram `{base_url}`、邮件 `{host, port, tls}`。漏声明一处，该字段就明文回显到浏览器；声明过头（把邮件 host/from/to 也遮）只让编辑变麻烦。
- 遮法：`MaskedValue` 产出 `__masked__:…<原值末 6 位>`；长度 ≤6 只回 `__masked__`，不给尾部提示（短凭据露末 6 位等于全露）。只露末段是因为辨识信息都在末尾——企微的 key、飞书的 hook id。非字符串凭据（webhook.headers 这个对象）整体遮成 `__masked__`。未知 kind 的 `MaskConfig` 返回空 map，不把含凭据的原配置吐回去；`MaskConfig` 只读，不动入参。
- 可逆标记：`__masked__` 前缀本身就是「沿用库中原值」的哨兵。`MergeConfig` 三分支——带前缀保留 stored、`TrimSpace==""` 删键、其余覆盖。`PrepareConfigUpdate` 把这条协议钉在写路径：任一 DestinationKeys 被改成新值，就必须对每个 SecretKeys 显式表态（给新值，或传空串表示不再需要凭据），回传掩码值或干脆不提该键一律拒，抛 `ErrDestinationChangedWithoutCredentials` 并点名 `Changed` 与 `Missing`。对应三条实测路径：只改 url 不提 headers，库里的 Authorization 发到对方端点；只改 base_url，`/bot<token>/sendMessage` 打到对方；只改 host，STARTTLS 后交出 SMTP 密码。这条路不依赖重定向，拒绝跨主机跳转挡不住它。
- 两个边界：`rejectMaskedInContainers` 必须最先跑（地址没变会提前返回，放后面只覆盖改地址这一条路），它拒掉把哨兵塞进对象内部的提交，否则字面量 `__masked__` 落库、后续鉴权静默失效；`sameConfigValue` 用 JSON 序列化比较并先把空串与缺键归一（`isBlankConfigValue`），否则 Telegram 留空的 `base_url` 从第二次保存起永久报「地址已变更」。
- 日志与错误同一口径：`redactRequestTarget` 只留 `scheme://host/…`，路径与查询全丢——凭据位置四家不同（钉钉 `access_token` 在 query、企微 `key` 在 query、飞书 hook id 在 path 末段、Telegram token 在 path 中段），按段打补丁漏一家就是一次泄露；`redactTransportError` 取 `*url.Error` 的 `Err` 字段，而不是事后替换字符串；`redactURLsInText` 兜住重定向策略这类自定义错误里的裸地址。凭据顺着 `last_error` 流向四个出口：`notification_deliveries.last_error` 列、投递历史接口、服务端日志、测试发送接口的 502 文本；`truncateNotifyError` 把该列截到 500 字节并回退到 rune 边界。凭据遮蔽不用哈希：这里要的是「回传即沿用」的可逆语义，哈希给不了；HMAC-SHA256 只用于签名。

## 出站安全

- 三层：配置阶段 `validateHTTPURL` 只放 `http`/`https`、要求 Host 非空、对字面 IP 做 `isBlockedDialIP` 预检；拨号阶段 `notifyTransport` 把 `Dialer.Control=blockInternalDial` 挂上，这里是最终生效点（覆盖 DNS 重绑定：校验时解析到公网、连接时解析到内网）；`emailDial` 挂同一个 `Control`，不挂就是整套防护的缺口。
- 网段清单（`isBlockedDialIP`）：`127.0.0.0/8` 与 `::1`（IsLoopback）、`169.254.0.0/16` 与 `fe80::/10`（IsLinkLocalUnicast，含云元数据 `169.254.169.254`）、`224.0.0.0/24` 与 `ff02::/16`（IsLinkLocalMulticast）、`ff01::/16`（IsInterfaceLocalMulticast）、`0.0.0.0` 与 `::`（IsUnspecified）、`224.0.0.0/4` 与 `ff00::/8`（IsMulticast）。先 `ip.To4()` 还原，否则 `::ffff:127.0.0.1` 是绕过口。RFC1918（10/8、172.16/12、192.168/16）刻意放行：内网自建 Mattermost 与 SMTP 中继是常见部署。确需打本机服务时用环境变量 `[前缀]_NOTIFY_ALLOW_LOCAL=1` 显式放行。
- 重定向：`CheckRedirect` 里 via 长度 ≥5 报过多，Host 与 `via[0]` 不同即拒跨主机；同主机补斜杠照常放行。
- 超时与体量：共用 `httpClient` Timeout 15s、Dialer Timeout 10s、响应体 `io.LimitReader` 8 KiB；邮件 `emailDialTimeout` 10s、`emailSessionTimeout` 45s，在建连处 `SetDeadline`（net/smtp 把连接藏在未导出字段，交出去后只剩预置 deadline 兜底）。通知客户端不复用渗透流量用的全局出口代理。

## 签名与鉴权

- 钉钉：待签串 `timestamp + "\n" + secret`，HMAC-SHA256 的 key 也是同一 secret，base64 后 URL 编码，timestamp 为毫秒，追加进 query，原有 `access_token` 不被覆盖；secret 为空原样返回地址。基准 `TS=1700000000000`、`SEC=SECtest123` → `w3RMHXzixTMdzr8OHJUmVLS4IoPJVdu+Ut1LE48MePE=`。
- 飞书：key = `timestamp + "\n" + secret`，message 为空，base64；timestamp 为秒，`timestamp` 与 `sign` 与 `msg_type` 同层进 body。同密钥基准 → `Hd4xFWQU6R6ad4nzy4ETIznzlqebqH7xcTFVmONTudo=`。两家刚好互为对方的参数顺序，照另一家写必然失败（飞书报 19021）。
- 其余：企微无加签，URL 上的 key 就是全部凭据，整个 webhook 地址同时进 SecretKeys 与 DestinationKeys；Telegram 走 `/bot<token>/sendMessage`；邮件 465 隐式 TLS 或 25/587 STARTTLS 后 `smtp.PlainAuth`，`MinVersion` TLS1.2，明文会话下 PlainAuth 拒发凭据，那条错误要翻译成「启用 TLS 或改 465」；webhook 鉴权全靠自定 headers。
- 签名每次发送现算，不缓存，平台侧时间窗口由钉钉与飞书判定。

## 失败模式与判据

- 静默失败：钉钉 `errcode`、企微 `errcode`、飞书 `code` 与 `StatusCode`、Telegram `ok` 四家都把业务错误塞在 HTTP 200 里，只判状态码会把失败记成成功。钉钉 301000 签名错、310000 关键词不匹配判永久；企微 93000 key 无效判永久、45009 限流判可重试；飞书 code 非 0 判永久；Telegram 429 可重试，400/401/403/404 判永久。
- 长度截断：企微 4096 字节超长整条被拒（不自动截断），客户端先截；kept 与实际投递行严格对应。
- 重复轰炸：滑动窗口清零点会在一秒内发两倍量，令牌桶按恒定速率补充避开。更隐蔽的是 digest 退化——rate=20 的渠道每 3 秒 tick 只补到 1 个令牌，把请求预算当批次大小会让每批只装 1 条漏洞。
- 误遮业务字段：凭据键漏声明 → 明文回显；目的地键漏声明 → `PrepareConfigUpdate` 保护不到改地址路径。
- 掩码绕过三形态：只改地址不提凭据、哨兵塞进对象容器、空串与缺键混判。
- 邮件退避：SMTP 4xx（450 灰名单、451、452）可重试，5xx（550、553）永久；`smtpStageError` 取错误文本前三位应答码，取不到按可重试处理。

## 与既有卡衔接

- 攻方视角看同一套机制（把通知机器人的 URL 参数当 SSRF 入口、用跳转与 DNS 重绑定绕过初检）：`domains/other/notify-bot-sms-ssrf`。
- 审计定位危险函数：`domains/file-vulns/code-audit/php/php-ssrf-audit`、`domains/other/src-methods/_vendor/sinian/sinian-ssrf-testing`。
- 集群内 webhook 受体当横向跳板：`domains/cloud-security/cloud/k8s-webhook-abuse`。
- 按栈反查本卡：tgsec-arsenal-router。
