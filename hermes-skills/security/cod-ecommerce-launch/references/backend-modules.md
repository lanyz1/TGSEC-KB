# COD 站后台功能扩展模式(实战: 马总COD 全模块)

单页 COD 架构铁律:**商品即落地页**——不做独立落地页体系,商品管理列表 = 落地页管理列表(预览图/标题/状态/像素/时间/操作+复制链接)。用户明确纠正过。

## 1. 后台模块开发模式(全部实测)

- 路由 `?s=admin&c={c}&m={m}` → admin.php 函数 `{c}_{m}`;每个方法开头 `admin_require()`,写操作打点 `ops_log('动作','详情')`(dr_ops_log 表)
- 列表页 view('admin_xxx') 传数据;Ozon 风格复用 admin_layout.php 的 admin_head/admin_foot + .card/.tbl/.stats/.badge/.btn 类
- 菜单:admin_layout.php 里 `$MENU` 数组(概览/业务/系统 3 组),url 填 `/index.php?s=admin&c=xxx&m=index`;**占位入口 data-placeholder="1" 要全改 0**(用户要求所有菜单真实可用)
- crumbMap 加 `'xxx' => '页面名'`
- 弹窗交互:原生 JS fetch + URLSearchParams POST,alert/自定义 tip 反馈,code:1 后 location.reload()
- 分页:GET page,每页 10,总数 COUNT + LIMIT/OFFSET

## 2. 组件化落地页编辑器(原生 JS 零依赖)

- 数据模型:dr_page(id, slug, title, config JSON {bg, components[]}),slug 随机 `p_` + md5 12位;route_by_slug 先查 dr_pro 再查 dr_page
- 组件 schema 双端一致:JS(LIB 数组:分组/图标/默认 props)+ PHP(page_render_component switch)
  - 已实现 17 种:title/text/image/fullimg/video/card/button/product/countdown/notice/label/faq/divider/space/footer/form/reviews
- 编辑器三栏:左组件库(点击/拖拽添加)→ 中手机预览 → 右属性面板(按 FIELDS schema 动态生成表单)
- 保存安全:PHP 端组件类型白名单校验(非法 type 拒绝),props 由渲染端 htmlspecialchars
- 手机预览 iPhone 17 Pro Max 规格:440px 宽(6.9" 1320pt@3x)、66px 外壳圆角+56px 内屏、钛金属渐变边框、灵动岛 128×38 悬浮(内容区顶部 spacer 66px 避让)、侧边按键
- 倒计时:props.end 转 timestamp → JS 每秒 tick;滚动公告:JS translateX 步进
- 评价组件(reviews):内置台湾姓氏/地区池随机生成 + 手机脱敏(09**-***####) + 时间"X分鐘前"动态

## 3. 本地上传安全(商品/落地页封面)

- 接口 admin_require + `$_FILES['file']`;校验:大小 ≤3MB → `getimagesize()` 真实图片(伪造后缀直接拒)→ 扩展名白名单 jpg/png/webp/gif → 随机文件名 `pro_Ymd_10hex.ext` → move_uploaded_file 到 `/uploads/`
- **uploads/.htaccess 必须禁 PHP**:`<FilesMatch "\.(php|php5|phtml|phar|pl|py|cgi)$"> Require all denied </FilesMatch>`(实测 403)
- 目录 chown apache:apache 755
- 前端:隐藏 file input + 按钮触发 + FormData fetch 上传 + 回填 URL + 预览

## 4. 多平台像素(商品级, 每落地页独立)

- dr_pro.fbpixel JSON 数组,元素格式:`纯数字` = Meta ID;`TikTok:ID` = TikTok 像素
- 保存接口校验:`/^\d+$/` 或 `/^[a-zA-Z]+:\s*[A-Za-z0-9\-_]+$/`,逗号/换行分隔
- 商品页注入(pro.php):主像素取后台 pixel_cfg 优先、商品纯数字 ID 兜底;PRO_PIXELS 输出 TikTok ttq 脚本(标准 sdk 代码)或额外 Meta 像素(fbq addPixelId + trackSingle PageView,与主像素不同才输出)
- pro_show.php 模板变量兜底:`$PRO_PIXELS = isset($PRO_PIXELS) ? $PRO_PIXELS : ''`

## 4b. 像素配置多账户系统(dr_pixel_cfg, 每配置绑定一个落地页)

用户要求"每个像素绑定一个商品页"的正式版——比 fbpixel 快速绑定更完整(独立 Access Token + 上报事件):

- 表: `dr_pixel_cfg(id, proid, name, remark≤500, pixel_id, access_token, event_name DEFAULT 'Contact', status, inputtime, updatetime)`;proid 关联 dr_pro,保存时校验商品存在
- 后台「像素回传」页下半区:配置列表(关联落地页标题+slug/配置名称/备注/Pixel ID/Token 截断/事件徽章/启用停用/编辑/删除)+ 新建弹窗(截图表单: 基础配置=关联落地页下拉+配置名称*+备注;Facebook API 配置=像素ID*+Access Token*+上报事件下拉 8 种: Contact/AddToCart/InitiateCheckout/Purchase/Lead/ViewContent/PageView/CompleteRegistration)
- **浏览器注入**(pro.php): `foreach (pixel_cfgs_by_pro(proid) as $pc)` → 每个配置输出独立 `fbq("init",id);fbq("trackSingle",id,event)`,与主像素相同跳过(避免重复 init)
- **CAPI 多配置转发**(order.php → pixel_purchase 传 proid): 循环每个启用配置, `pixel_send_capi_raw(event, pixel_id, token, user, custom, "pixelcfg{id}.{sn}")` 独立 token/独立事件/独立 event_id, 每条 `pixel_log_event` 记录 sent/fail——一个商品页可同时向多个广告账户独立归因
- 启停即时生效: status 切换后商品页注入/停止注入(停用测试: grep 像素 ID = 0)
- 全局 pixel_cfg = 默认像素, 商品配置 = 叠加(互不干扰)

## 5. Telegram 订单通知

- lib/tg.php:配置存 dr_settings k=tg_notify{bot_token,chat_id,enable};tg_send 用 file_get_contents POST api.telegram.org/bot{token}/sendMessage
- **拿 chat_id 技巧**:后台「自动获取」按钮调 getUpdates,取最近 message.chat.id 自动填入——用户只需先给机器人发一条消息
- 下单成功 order.php 挂 tg_notify_order(失败静默,不影响下单);消息含订单号/金额/收货人/电话/地区 + 后台详情链接
- 服务器需能直连 api.telegram.org(香港/海外 IP 没问题;国内服务器要代理)

## 6. 后台一键域名绑定(免 SSH)

- sudoers 白名单(实测必需):
  ```
  Defaults:apache !requiretty
  apache ALL=(root) NOPASSWD: /bin/cp /tmp/zengda_http.conf /etc/httpd/conf.d/zengda.conf, /bin/cp /tmp/zengda_https.conf /etc/httpd/conf.d/zengda-le-ssl.conf, /usr/bin/systemctl reload httpd, /bin/systemctl reload httpd, /usr/bin/certbot *
  ```
  先 visudo -c 校验再 install -m 440
- 流程:域名校验 → DNS 预检(gethostbyname == 服务器IP,未解析拒绝)→ PHP 生成 80+443 双 vhost(ServerName=新域名,ServerAlias=全部,443 证书固定指向主证书)→ sudo cp + reload → certbot `--webroot -w /var/www/zengda -d 全域名 --cert-name 主证书 --expand --non-interactive --agree-tos` → 改 config.php site_domain
- 80 vhost 跳转规则必须排除 `^/\.well-known/acme-challenge/`(否则 webroot 验证被 301 到 https 失败)
- PHP web 层 exec() 可用(disable_functions 空);域名已严格校验防注入

## 7. Meta CAPI 实测经验

- 像素设置页生成的 **Dataset Quality API token(SYSTEM USER, scopes 只有 read_ads_dataset_quality)可以 POST events**:`graph.facebook.com/v{20-23}/{pixel_id}/events` 返回 `{"events_received":1}`(不需要 ads_management)
- debug_token 验证: `v22.0/debug_token?input_token=X&access_token=X` → is_valid + scopes + target_ids
- 像素 events 端点 v20.0 到 v23.0 全部可用(2026-08 实测)
- 商品页像素注入检查:curl 商品页 | grep -c "fbq('init'" / "TiktokAnalyticsObject"

## 8. 测试残留清理纪律

- 每次功能实测后清理:dr_page/dr_page_lead/dr_pro 测试商品/dr_blacklist/dr_ops_log;用户上线前要求全清
- 列表页 grep 验证注意:**HTML 单行时 grep -c 只算 1 行,统计条目用 `grep -o '关键词' | wc -l`**
