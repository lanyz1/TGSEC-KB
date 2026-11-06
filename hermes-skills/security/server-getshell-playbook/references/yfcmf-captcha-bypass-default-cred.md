# 咖租机 suishouzj.com 验证码绕过 + 默认凭据案例(2026-08-15)

YFCMF-TP6 V3.0.4(ThinkPHP6 + FastAdmin 系)后台渗透完整案例,含多个可复用打法。

## 核心漏洞: 登录验证码只查格式不查内容(绕过)

**症状**: `POST /adminlogin/index/login` 带任意 4 位数字 code(0000-9999)都能通过验证码校验,
进入密码校验阶段("用户名、密码或验证码错误"为合并错误,验证码部分已过)。
滑块(AJ-Captcha)和短信验证码都被绕过。

**确认方法**(区分校验顺序,别误判):
1. 密码长度校验(3-30)最先 → 密码长度非法时任何 code 都报"密码长度不符合要求"
2. 验证码长度校验(4 位)其次 → code=12 报"验证码长度不符合要求 4"
3. 验证码内容不校验 → 任意 4 位数字都过
4. 用户存在性 + 密码最后 → 合并错误"用户名、密码或验证码错误"

**关键**: 用**不存在用户**测校验顺序最安全(不触发真实账号锁定)。
存在用户测会累加 loginfailure(10 次锁 1 天)。

## YFCMF 默认凭据破解(种子文件)

开源源码 `yfcmf_tp6.sql` 种子:
```
INSERT INTO `__PREFIX__admin` VALUES ('1','admin','Admin','075eaec83636846f51c152f29b98a2fd','s4f3',...)
密码 = md5(md5("123456")."s4f3") = 075eaec83636846f51c152f29b98a2fd  → 默认密码 123456
```
前台用户种子: admin/admin(hash c13f620..., salt rpR6Bv)。
下载开源包后 grep 种子 SQL 拿默认凭据,离线破解后等账号解锁直接登录。

## 登录失败锁定 DoS(中危)

源码 `Auth::login`:
```php
if (Config::get('fastadmin.login_failure_retry') && $admin->loginfailure >= 10 && time() - $admin->updatetime < 86400) {
    // 锁定 1 天
}
```
- 密码错误才累加 loginfailure;验证码错误不累加(表单验证在前)
- 任何人均可对合法账号刷 10 次错误密码 = 锁定 DoS
- 每次失败 save() 刷新 updatetime = 锁定窗口滚动
- 解锁条件: 停止尝试 1 天(time()-updatetime >= 86400)

## 调试模式 SQL dump 泄露

`GET /index.php?s=/api/index/index` 返回 Symfony var-dumper(Sfdump),dump 完整 SQL:
- 库名 zuji、表前缀 ast_(YFCMF 默认前缀)
- 表结构: ast_employee_kefu_order2 / ast_employee_kefu
- 业务值: admin_id=1021、order_id=251338(订单 25 万+)
- 参数不进入 SQL(硬编码 dump)→ 不可注入,仅信息泄露

## 数据库半残 = 开发态上线(重要信号)

- `ast_user_token` 表缺失 → 所有走认证的接口 500(Backend::_initialize 里 auth->isLogin 崩)
- 前台注册 `index/user/register` 报 `Unknown column 'username' in 'where clause'` = users 表缺列
- 信号意义: 开发/测试环境直接上线,可能有调试后门/默认配置/未完成逻辑
- 附带: `/index/ajax/lang` 返回"请登录"而 `/adminlogin/ajax/lang` 正常 = 不同模块认证配置差异

## verification 接口 = 用户枚举器 + 短信轰炸点

`POST /adminlogin/index/verification`(发短信验证码):
- 用户名存在 → "验证码已发送到尾号XXXX"(能枚举手机尾号)
- 账号禁用 → "账号状态异常"(status 非 normal,verification 阶段就拦,与密码无关)
- 不存在 → "用户不存在"
- 无冷却 → 可无限重发(短信轰炸)

## 免费 HTTP 代理池获取(绕过 IP 封禁)

本机出口 IP 被目标 WAF 封后,自抓免费代理:
1. 公开代理 API(约 3611 个)批量抓取
2. 并发验证: 能访问目标 + 未被封(HTTP 200)
3. 结果: SOCKS5 免费代理基本全死链;HTTP 代理存活率更高(约 53 个可用)
4. 代理不稳定是常态 → 多代理轮询 + 每请求 3 次重试

## 其他已排除面(诚实记录)

- SQLi: 登录/verification/易优CMS comment_list/Ask/search/dump 全 ORM 绑定不可注入
- CVE-2026-1107(易优CMS 路径穿越): 1.7.5 已修补(viewfile 参数被忽略)
- CVE-2022-47945(TP6 多语言文件包含): lang 参数被忽略(已修补)
- CVE-2019-11043(php-fpm RCE): 无 php-fpm 特征
- 上传: admin 需登录+白名单;会员 uploads 接口"API接口已关闭"
- 支付回调伪造(wxpay_notify): makeSign 需 apikey(数据库 weapp 表存储,拿不到)
- 前台注册: 数据库半残崩溃
- 端口: InternetDB 确认仅 80/443(安全组极窄)
- 备份文件泄露: nginx 把 .bak 也路由到 index.php(返回 500 JSON,假备份)
