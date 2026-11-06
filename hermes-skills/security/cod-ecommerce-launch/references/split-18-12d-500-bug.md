## 12d. 下单提交不跳转/500 完整排查链(三层 bug 叠加)⭐

症状: 手机号栏红字提示、或提交后无反应/提示失败、或 500。**三层问题可叠加, 逐层排**:

**① 前端字段校验过严(卡在具体字段)**: 台湾手机规则 `/^(09|9)\d{8,8}$/` 会拦截任意测试号(如 `3132901982` 31 开头)→ 提示「請填寫正確手機號碼」卡字段。修复: 放宽为 `/^\d{8,15}$/`(纯数字 8-15 位)——**前端 pro_show.php 与服务端 order.php 的校验必须同步改**, 否则前端过了后端 500/拦截。

**② 前端提交函数依赖缺失(提交请求根本不发出)**: 商品页 `skuComponent.redirectTocamll()` 调 `layer.load()` 但页面从未引入 layer 库 → `ReferenceError` → **$.ajax 提交永不执行**(点提交显示"提交中…"后无任何网络请求)。修复: 自托管 layer 3.5.1(bootcdn 下载 layer.js + theme/default/{layer.css, loading-0/2.gif})到 `/static/assets/lib/layer/`, head 引入(在 jquery 后)。诊断关键: Network 层抓 `s=order` 请求——**0 请求 = 前端卡死, 有请求看响应**。

**③ 服务端 500: PHP Error 不被 try/catch(Exception) 捕获** ⭐: order_buy 里 `try { tg_notify_order([...]); } catch (Exception $e) {}` —— 若 tg_notify_order 参数不匹配(如函数签名要 3 参、调用只传 1 参)→ `ArgumentCountError` 是 **Error 不是 Exception → 直接 Fatal 500(空 body)**。修复: 参数给默认值 `array $pro = [], array $skuVal = []`。**教训: 改函数签名时 grep 全部调用点; 下单链路任何改动后必须服务端 POST 实测**(GET 页面拿 `csrf_test_name` + cookie jar → POST `?s=order&c=order&m=buy&mid=pro&id=61&sku=0_0&num=1&huilu=1&ccode=` 带全表单 data[name/phone/city/address...] + paytype=nopay, 期望 `{"code":1}`)。这也解释了"之前能下单、某次改动后不能"——**回查最近改动过的调用链**。

**④ head 同步脚本阻塞 body 解析(页面 200 但 body 不出)**: 远程 CDN script(lazysizes 等)在 head 同步加载, CDN 慢/被墙 → body 永不解析。修复: 本地化 `/static/js/lazysizes.min.js`(本地有副本直接换)。

