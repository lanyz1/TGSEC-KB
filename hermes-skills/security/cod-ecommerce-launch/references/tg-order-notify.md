# Telegram 订单通知 — 完整实现模式

COD 电商站新订单即时推送到站长 TG。2026-08 zengda/xeelee.top 实战, 全部实测通过。

## 架构

```
order_buy 成功 → tg_notify_order($order, $pro) → tg_send($text)
    ↓ (失败静默, 不影响下单)
后台系统设置 → 订单通知卡片 (bot_token / chat_id / enable / 测试按钮 / 自动获取)
```

- 配置存 `dr_settings` k=`tg_notify`(JSON: bot_token/chat_id/enable)——与 pixel_config/cloak_config 同模式
- 发消息用 `file_get_contents` + `stream_context_create`(无需 curl 扩展), 10s 超时
- 全部 try/catch 静默, 通知失败绝不影响下单链路

## lib/tg.php 核心

```php
function tg_config(): array { /* 读 dr_settings tg_notify, 默认空 */ }
function tg_save_config(array $c): void { /* INSERT OR REPLACE INTO dr_settings */ }
function tg_send(string $text): array {
    $url = 'https://api.telegram.org/bot' . $token . '/sendMessage';
    // http_build_query + stream_context POST, 10s 超时
    // 返回 ['ok'=>bool, 'msg'=>...]
}
function tg_notify_order(array $order, array $pro): void {
    if (empty($cfg['enable'])) return;
    $txt = "🛒 新订单通知\n━━━\n📦 订单号: ...\n💰 金额: ...\n👤 收货人: ...\n📍 地区: ...\n🔗 https://" . cfg('site_domain') . "/index.php?s=admin&c=order&m=show&sn=...";
    tg_send($txt);
}
```

## 后台三个方法(modules/admin.php)

1. `tg_save()`: 收 bot_token/chat_id/enable → tg_save_config → ops_log
2. `tg_test()`: **先保存再发**(用户可能只填了 token 就点测试, 测试前落库保证后续一致); 发 "✅ 订单通知已接通\n服务器: ..."
3. `tg_getupdates()`: 调 `api.telegram.org/bot<token>/getUpdates` → 遍历 result[].message.chat.id 去重 → 取第一个自动存为 chat_id, 返回消息 "已自动填入 chat_id=xxx (来自 @yyy)"

## 前端(admin_settings.php 订单通知卡片)

- input#tg_token / input#tg_chatid + 「自动获取」按钮(调 getupdates, 成功后 `msg.match(/\d{5,}/)[0]` 回填)
- checkbox#tg_enable + 保存/测试按钮 + tgTip 提示条(绿/红)
- 配置回显: settings_index 里 `$tg['bot_token'] = substr(...,0,12).'…'` 脱敏

## 下单挂钩(order_buy 内, CAPI 回传之后)

```php
try {
    require_once __DIR__ . '/../lib/tg.php';
    tg_notify_order([...sn/inputtime/name/tel/money/region_name/note...],
                    ['title' => $skuData['group'][0] ?? '商品']);
} catch (Exception $e) {}
```

## 验证方法

- 无 token 时 tg_test/tg_getupdates 返回友好错误(`{"code":0,"msg":"请先填写..."}`)
- 真实测试: 用户填 token 后点测试按钮 → TG 收到消息即全链路通
- 端到端: 开 enable 后下一个真实订单, TG 收到订单卡片(含后台详情链接)

## BotFather 注册流程(交付给用户)

1. TG 搜 @BotFather → `/newbot` → 填显示名 → 填用户名(必须 `bot` 结尾) → 得到 Bot Token
2. 给机器人发任意消息(START) → 后台粘贴 token → 点「自动获取」自动填 chat_id
3. 测试按钮验证 → 勾选启用 → 保存
4. 群通知: 建群拉机器人进群 → 群里发消息 → 自动获取得到群 ID(负数 -100...)
5. token 泄露: BotFather `/revoke` 吊销重发

## 坑

- exec_command 传 PHP heredoc 无输出 → 脚本写文件上传再执行(见主 SKILL.md §8)
- getUpdates 只返回最近的 update(offset 未用), 用户没给机器人发过消息时 result 为空 → 返回引导文案
- 服务器到 api.telegram.org 直连(独立 IP 服务器一般通); 走代理环境才需要 curl 代理参数
