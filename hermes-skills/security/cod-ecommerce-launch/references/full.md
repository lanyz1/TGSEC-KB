---
name: cod-ecommerce-launch
description: "COD电商站部署上线: CentOS+PHP+SQLite/HTTPS/斗篷/像素。触发: 部署、上线、绑域名、斗篷。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# COD 电商站生产部署与上线

覆盖: 长安COD/迅睿CMS系重建版(PHP+SQLite)从本地到生产服务器的完整上线: 环境安装、代码同步、域名+HTTPS、数据迁移、营销配套(斗篷/像素回传)、上线收尾清单。

## When to Use

- 重建版/新站部署到 Linux 服务器(用户自有资产)
- 绑定域名 + HTTPS + 上线检查
- 新增斗篷风控 / Meta 像素回传 / 后台品牌改名

## 1. 服务器侦察(先做)

paramiko SSH → 查 OS/CPU/内存/磁盘/已装软件(PHP/Apache/Nginx/宝塔)/防火墙/监听端口。
CentOS7 最小化典型状态: 无 firewalld(iptables ACCEPT 无过滤), rpcbind(111 公网可达, 停)、postfix(25 仅本机, 可停)、sshd 非标端口。

## 2. 环境安装(CentOS7 + PHP 8.2)

```bash
yum install -y epel-release
yum install -y https://rpms.remirepo.net/enterprise/remi-release-7.rpm
yum-config-manager --enable remi-php82
yum install -y httpd mod_ssl php php-cli php-pdo php-sqlite3 php-mbstring php-xml php-json
timedatectl set-timezone Asia/Shanghai
```

- **大坑: CentOS7 自带 SQLite 3.7.17 不支持 UPSERT(需要 3.24+)**。代码里所有 `INSERT ... ON CONFLICT(k) DO UPDATE SET v=excluded.v` 在服务器上抛 `PDOException: near "ON": syntax error`(500, Content-Length 0)。**一律用 `INSERT OR REPLACE INTO`**(全版本兼容)。写 PHP+SQLite 代码时直接只用 OR REPLACE, 别用 UPSERT 语法。
- php.ini: `display_errors=Off` + 追加 `error_log=/var/log/php_errors.log`(chown apache)

## 3. 代码上传(本地/服务器配置分离!)

- 本地 tar.gz → SFTP 上传 → 服务器解压到 /var/www/<site>
- **大坑: 批量同步把本地开发 config.php 覆盖服务器生产配置**(后台密码被改回 admin123, 之后的"登录成功"全是登录页假阳性)。上传文件列表**排除 config.php**, 部署后用 sed 单独写服务器配置; 或上传后立即校验 `grep admin_pass config.php`。
- 权限: `chown -R apache:apache` + `find data -type f -exec chmod 664 {} \;`; SELinux: `chcon -R -t httpd_sys_content_t`
- httpd vhost: `AllowOverride All` + `Options -Indexes`(伪静态 .htaccess 生效)

## 4. 域名 + HTTPS(Let's Encrypt)

- 先确认 DNS(A + www → IP); **Let's Encrypt 的 DNS 视角与本地不同步**: www 刚解析时 LE 挑战报 `SERVFAIL looking up A`。先签主域, www 传播后再补, 最后合并:
  `certbot --apache -d xeelee.top -d www.xeelee.top --cert-name xeelee.top --non-interactive --agree-tos --redirect --expand`
- **坑: 分开签的两个证书会让其中一个域名拿到 CN 不匹配的证书**(openssl 验证 SAN 只有 www)。必须 expand 合并成单证书 SAN 双域名。
- HTTP→HTTPS 301: certbot `--redirect` 自动配; 续期 `certbot renew` 自带 cron。

## 5. 数据迁移(地区库/大表)

- 从线上 API 抓全量: 逐层 BFS + ThreadPoolExecutor(8) + **每层即时 commit + flush 输出**(别在最后才 commit, 中断全丢)。
- **大坑: BFS 会把末级节点也当父级再发请求**(tw711 7474 个门市 × 2s/请求 ≈ 30 分钟空转)。必须**深度限制**: queue 存 (pid, depth), depth >= max_depth 只记录数据不再请求子级。门市/末级树按 code 设 max_depth=2~3。
- 跨库合并: 上传本地库到 /root/local.db → 服务器 PHP `ATTACH` + `INSERT OR IGNORE INTO dst SELECT ... FROM src`(**不要整库覆盖**, 保留服务器订单/设置)。**ATTACH 必须在目标连接上执行**(`$dst->exec("ATTACH '/root/local.db' AS src")`, 再 `$dst->exec("INSERT ... FROM src.dr_linkage")`)—— attach 到源连接会报 `no such table: src.dr_linkage`。注意 exec_command 直接传 PHP heredoc 可能无输出(EXIT 255), 把脚本写成文件上传再执行更稳。

## 6. 营销配套

- **斗篷风控**(11 规则引擎/回流页/HMAC 管理员放行/测试方法): 见 `references/cloak-risk-control.md`
  - **坑: 管理员放行检查必须在黑名单检查之后且 `return []`(不是 return $hits)**——放行优先级最高, 否则被自动拉黑的 IP 登录后台后访问落地页仍被拦(修复: `if (cloak_back_ok()) return [];`)
- **Meta Pixel + CAPI 回传**(Graph API v20/SHA256 哈希/多像素/测试事件): 见 `references/cloak-risk-control.md` 第二节
  - **CAPI token 配置与实测**(用户提供 Pixel ID + token 后): ① 后台 pixel save API 写入 → ② 商品页 `grep -c <new_id>` 应 >0 且旧 ID 残留 0——**旧 ID 残留位置在 SKU JSON 的 `fbpixel` 字段**(商品自带兜底), 需同步 `UPDATE dr_pro SET fbpixel='["<new_id>"]'` → ③ `graph.facebook.com/v22.0/debug_token?input_token=<t>&access_token=<t>` 验证 token: SYSTEM USER + `read_ads_dataset_quality` scope 也能发 events(实测 HTTP 200 `events_received:1`)——**Dataset Quality 只读 token 足够 CAPI 发事件**, 不需要 ads_management; ④ events 端点 v20.0 在 2026-08 仍可用, 不必急着升 API 版本
- **Telegram 订单通知**(后台配置 + getUpdates 自动 chat_id + 下单挂钩): 见 `references/tg-order-notify.md`
- 品牌改名: 全站 grep 目标词 → 批量替换源码文件 + 删除 curl 测试残留 html → 同步服务器 → 服务器 grep 残留=0 验证。

## 7. 上线收尾清单

- [ ] 清测试数据: dr_order/dr_weblog/dr_fb_event/dr_cloak_log/dr_cloak_visit/dr_blacklist(保留 dr_pro/dr_linkage/dr_settings); 清完用 COUNT(*) 逐表验证=0
- [ ] 斗篷总开关默认关闭; 推荐配置写进运维文档(回流页 URL 必须填, 否则命中显示白页)
- [ ] **回流页文件必须真实存在**(back.html 等): 斗篷命中 JS 跳转, 文件缺失 = 404 白屏(隐蔽坑, 上线核查必测 `curl -k -o /dev/null -w '%{http_code}' https://域名/back.html`)
- [ ] 像素实测: debug_token 200 + events 端点 `events_received:1`(token 有效性最终证明, 不是"保存成功")
- [ ] SQLite 每日备份 cron: `sqlite3 db ".backup '...'"` 或 cp, 保留 7 天
- [ ] 停 rpcbind/postfix; 装 fail2ban(sshd 非标端口 jail + http-get-dos); 核查 `ss -tlnp` 只剩 80/443/SSH
- [ ] 运维手册(账号/备份恢复/代码更新流程)上传 /root/
- [ ] 生产回归: HTTPS 端到端下单(登录态 + CSRF)且后台能搜到订单

## 8. 测试/验证坑(curl / shell)

- **URL 带 `&` 必须整体加引号**, 否则 shell 拆成后台任务 → 保存 API 静默失败(斗篷"没开"假象, 排查半天)
- Windows 原生 curl 写 `/dev/null` 失败(exit 23)→ 用 `-o NUL`
- cookie jar 域名匹配: 请求 `127.0.0.1` + Host 头时, jar 里以域名为域(如 xeelee.top)的 cookie **不会发送** → 测试手动 `-H 'Cookie: name=value'`
- HTTPS 站点测试: 必须 `curl -k https://...` + Host 头; http 会 301
- **验证"登录成功"看 302 Location 或业务内容, 200 不等于成功**(登录页也是 200!)
- Python `-c` 多层引号易炸 → 写脚本文件; paramiko exec_command 传复杂 heredoc 可能丢输出 → 先 write_file 上传再执行
- 本地与服务器的 cfg() 实现可能不一致(本地支持无参返回全量, 服务器必须带 key)——传配置数组到模板时逐键 cfg('key') 显式取, 别用 cfg()
- PDO execute 的数组必须从 0 连续索引: array_unique/array_filter 会保留原键, 导致 `bind or column index out of range`(500), 加 array_values() 重排
- 长抓取/安装放后台跑(notify_on_complete), 别占前台超时(用户会中断)
- **PHP PDO 绑定坑: `array_unique(array_filter(array_column(...)))` 返回非连续键数组, PDO execute 按键索引绑定 → `SQLSTATE[HY000] column index out of range`(500 无输出)。任何要传给 execute() 的数组一律 `array_values()` 重排**(区域管理父级 IN 查询实战)

## 9. 后台模块扩展(占位菜单 → 真功能)

后台侧边栏占位菜单(商品/区域/IP黑名单/操作日志/系统设置/关于)转真模块四件套:

1. `templates/admin_layout.php`: 菜单项 url 从 `'#'` 改为 `/index.php?s=admin&c=<mod>&m=index`(去掉 data-placeholder="1" 即不再弹"开发中" toast) + crumbMap 加 `'<mod>' => '中文名'`
2. `modules/admin.php`: 加 `function <mod>_index()`(admin_require + 查询 + view) + 编辑/删除 POST 方法返回 `{"code":1}`
3. `templates/admin_<mod>.php`: `require admin_layout.php; admin_head('标题', '<mod>')` + `.stats` 统计卡(5 卡网格) + 筛选卡 + `.table-wrap` 表格 + 分页
4. 编辑/删除前端 fetch POST, alert + location.reload()

模式要点: 统计卡/搜索/分页全部复用 admin_layout 的 CSS 类(.stat/.c-blue/.btn/.badge/.tbl), 零新样式; 分页 = `LIMIT n OFFSET m` + COUNT(*) 双查询; 父级名称同表 `WHERE region_id IN (...)` 预加载 map。完整实现示例(区域管理 15483 条浏览/筛选/搜索/编辑/删除): `references/admin-module-pattern.md`

**区域树维护(地区=树, 下单联动即时生效)**: 每行操作 `[+ 下级] [编辑] [删除]`; 添加下级 = `MAX(region_id)+1` 组内新 ID + `INSERT OR IGNORE`(防冲突)+ 同组 parent_id 存在性校验; 编辑弹窗含名称/编码/邮编/**父级(region_id, 0=顶级)**; **防环铁律**: 父级不能是自己(`$pid === $row['region_id']` 拒)+ 不能移到自己的后代(沿 parent_id 链向上走, 遇到自己即拒); `parent_id=0` 是顶级标记——**0 必须跳过存在性检查**(否则误报"父级地区不存在")。保存后下单页地区联动**即时可见**(同一 linkage_ld 接口)。

## 10. 后台自助域名绑定(一键切换, sudoers 白名单模式)

用户要求后台能自己绑域名/切换主域名, 不碰服务器时用的模式: **PHP(apache 用户) exec → `sudo -n` 白名单 root 命令**。

1. **sudoers**(/etc/sudoers.d/zengda, 先 `visudo -c -f` 校验再 install -m 440; **`Defaults:apache !requiretty` 必须**——apache 无 TTY):
   ```
   Defaults:apache !requiretty
   apache ALL=(root) NOPASSWD: /bin/cp /tmp/zengda_http.conf /etc/httpd/conf.d/zengda.conf, /bin/cp /tmp/zengda_https.conf /etc/httpd/conf.d/zengda-le-ssl.conf, /usr/bin/systemctl reload httpd, /bin/systemctl reload httpd, /usr/bin/certbot *
   ```
2. **vhost 双文件结构**: 80 段(zengda.conf, ServerName + ServerAlias + 全量 https 跳转)+ 443 段(zengda-le-ssl.conf, 证书固定指向 live/<cert-name>/)。PHP 生成内容写 `/tmp/zengda_*.conf`(apache 可写)→ `sudo -n /bin/cp` 安装 → `sudo -n systemctl reload httpd`
3. **一键绑定流程**: 域名格式校验(`/^[a-z0-9]([a-z0-9\-\.]*[a-z0-9])?$/i`)→ **DNS 预检**(`gethostbyname($d) === 服务器IP`, 未解析直接拒绝不白签; www 也解析就一起绑)→ 新域名做 ServerName 其余做 ServerAlias → 安装 + reload → **certbot --webroot expand 全部域名进主证书**(单证书 SAN 全域名, 续期一次管全部)→ 改 config site_domain
4. **大坑: 80 段跳转规则必须排除 acme 验证路径**, 否则 webroot 挑战被 301 到 https → 签发失败:
   `RewriteCond %{REQUEST_URI} !^/\.well-known/acme-challenge/`
5. **不要用 certbot --apache 自动改 vhost**(它按 ServerName 拆段/覆盖证书行, 多域名结构不可控); 用 `certbot --webroot -w <docroot> -d d1 -d d2 --cert-name <主证书> --expand --non-interactive --agree-tos --email admin@<主域名>`
6. **验证 exec 链路**: 临时 web 探针 `exec('sudo -n /bin/systemctl reload httpd 2>&1', $o, $rc)` 返回 rc=0 即通, 测完删探针。`sudo -u apache sudo -n <cmd>` 可先 shell 层验证。
7. 后台页面: 统计卡(域名数/主域名/证书到期/证书 SAN)+ 绑定列表(主/别名徽章, 设为主域名/移除)+ 添加表单; 保护: 不能移除当前主域名。

详细实现(生成 vhost 的 PHP 函数/证书到期解析/实测结果): `references/domain-bind-sudoers.md`

## 11. 配置类接口的 POST 覆盖坑

- **`isset($_POST['key'])` 就覆盖已存配置的接口, 测试时传占位符会把真配置破坏**(实测: tg_getupdates 传 `bot_token=USE_SAVED` 把真 token 覆盖, 后续全部 404)。测试这类接口要么传真值, 要么设计成"空则不覆盖"。类似地, tg_save 类接口保存前先 `array_merge(tg_config(), $c)` 防字段缺失清空。

## 11b. 后台图片本地上传模式(商品管理/任意表单)

- **uploads 目录**: `<docroot>/uploads/`(chown apache:apache 755), 上传接口 POST `?s=admin&c=product&m=upload`(admin_require + `$_FILES['file']`)
- **校验链**: ① error 码 → ② 大小 ≤3MB → ③ **`getimagesize()` 真实图片校验**(伪造后缀直接拒) → ④ 扩展名白名单 `[IMAGETYPE_JPEG=>jpg, PNG, WEBP, GIF]` → ⑤ **随机文件名** `pro_<date>_<md5 10位>.<ext>`(不可预测) → move_uploaded_file + chmod 0644 → 返回 `{code:1, url:'/uploads/xxx'}`
- **安全铁律: uploads/.htaccess 禁 PHP 执行**(上传点即使被塞 webshell 也无法运行):
  `<FilesMatch "\.(php|php5|phtml|phar|pl|py|cgi)$"> Require all denied </FilesMatch>`(实测 403)
- **前端**: 隐藏 `<input type=file accept="image/*">` + 「📁 选择图片上传」按钮触发 → FormData fetch 上传 → 回填隐藏 URL 输入框 + 预览 div(内联 img); 弹窗里预览占位 56×56 灰底「无图」
- **编辑弹窗数据源**: 专用 `product_get` 接口返回全量(标题/slug/主图/全部价格档数组 vals:[{key, price, yprice, qty}]), 弹窗按 vals 动态生成每档三输入(售价/划线价/库存, `data-k="price_<key>"`), 提交时 collect 全部 `[data-k]` 输入 → product_edit 按 `price_(\d+)_(\d+)` 正则循环回写 sku_json
- **主图同步三处**: dr_pro.thumb + sku_json.thumb + sku.image['0']['0'] + value['0_0'].image(只改一处会导致落地页/列表/详情图不一致)

## Verification

- [ ] 环境: php -v / httpd -t / php -m 含 pdo_sqlite
- [ ] 站点: 商品页 200 + 后台登录 302→dashboard
- [ ] 域名: https://主域 与 https://www 均 200, 证书 SAN 含双域名, http 301
- [ ] 回归: HTTPS 端到端下单 code:1 + 后台可见

## 12. 组件化落地页编辑器(投手自助建页, 零前端依赖)

投手要能自己新建/改落地页(参照 SAAS 落地页工具的组件库+手机预览模式), 纯原生 PHP+JS 实现的模式:

1. **数据模型**: `dr_page(id, slug UNIQUE, title, config JSON, status, hits, inputtime, updatetime)` + `dr_page_lead(pid, name, tel)`(表单线索); slug 自动生成 `p_<md5 12位>`, 接入 `route_by_slug`(pro 查完查 page)
2. **配置 JSON 双端渲染**: `{bg, components:[{type, props}]}` —— 前端编辑器 JS `renderComp()` 实时预览, 前台 `modules/page.php` `page_render_component()` PHP 渲染, 两套实现同一组件 schema(必须保持一致)
3. **编辑器三栏布局**(单模板内联 JS/CSS): 左=组件库(分组: 基础/媒体/转化/内容, 点击或拖拽添加)→ 中=手机预览(390px 模拟, HTML5 drag 排序 + 选中高亮 + 上移/下移/删除浮层)→ 右=属性面板(按 FIELDS schema 动态生成表单, onchange 实时 setProp 重渲染)
4. **组件集(16 个够用)**: title/text/divider/space/image/fullimg/video/card/button/product/countdown/notice/label/faq/footer/form; 商品卡组件从 dr_pro 读真实商品(图/价/购买链), 倒计时前台 JS 每秒 tick, 公告 CSS transform 滚动
5. **安全**: page_save 服务端校验 JSON + 组件 type 白名单(非法直接拒); 文本 htmlspecialchars; 链接仅 http(s)
6. **API 测试陷阱**: 控制器函数结尾 `exit`(json_out 风格), 同进程连续调用测试脚本会被截断——逐进程测或直接 curl 服务器实测
7. 完整 schema/编辑器 JS 结构/实测结果: 见 `references/page-builder.md`

## 12b. 商品=落地页融合 + 多平台像素(用户纠正)

- **单页 COD 架构铁律: 商品即落地页, 不做独立落地页体系**。商品管理列表 = 落地页管理列表(预览缩略图/落地页标题+slug+浏览/状态徽章/像素设置列/创建时间/操作: 发布取消·复制链接·⋯更多编辑删除) + 分页 10/页 + 搜索
- **「合二为一」用户语义(纠正过, 中间态)**: 用户说合并时 = **入口融合但功能全保留**。落地页管理页 = Tab 切换 `[🛒 商品落地页 (N)] [🧩 自定义落地页 (N)]`, 两个新建按钮按 Tab 切换显示; 自定义落地页(组件编辑器 dr_page)并入同页 Tab 展示(编辑仍进 page_editor), page 模块 API 全保留。**删菜单入口 ≠ 删功能**——合并前先确认保留项, 代码保留 URL 可访问(曾误删自定义落地页入口被用户纠正)
- **最终态(用户再决策, 方案A, 覆盖中间态)⭐**: 商品落地页和自定义落地页**彻底合并为纯卖货页列表**——「+ 新建自定义页」按钮、dr_page 数据(含 dr_page_lead)、相关 JS(pageAdd/pageToggle/pageDel)全删, 自定义落地页体系砍掉; 其**营销组件(倒计时/最新评价)并入商品详情编辑器**(见 12f)。落地页管理 = 唯一入口只列商品, 统计「共 N 条」。**决策链教训**: 用户先要"合二为一"→ Tab 并存 → 问"这个有用吗"(截图圈住自定义页按钮)→ 诚实分析(不能下单/无像素/唯一差异是营销组件)→ 用户选 A。**新功能上马前先问业务价值, 别默认保留; 砍功能要清干净(按钮+数据+JS 残留), 用 grep -c 验证 0 残留**
- **模板变量冲突坑**: 同页传 dr_page 列表 `$pages` 时, 分页变量不能再叫 `$pages`(`$pages = max(1, ceil(...))` 会覆盖列表)→ 分页改名 `$pageCount`
- **商品级多平台像素**: `dr_pro.fbpixel` JSON 数组, 元素支持 `纯数字`(Meta ID)或 `TikTok:ID`(带平台前缀); 保存接口校验 `^\d+$` 或 `^[a-zA-Z]+:\s*[A-Za-z0-9\-_]+$`; 像素设置弹窗逗号/换行分隔多 ID
- **像素配置多账户系统(dr_pixel_cfg)**: 每条配置绑定一个商品页(独立 Pixel ID + Access Token + 上报事件下拉), 商品页自动注入 fbq init+trackSingle, 下单 CAPI 逐配置独立 token 转发(多广告账户独立归因)——详见 `references/backend-modules.md` §4b
- **页面注入**(pro.php): 主像素 = 后台 pixel_cfg 优先, 商品纯数字 ID 兜底; 额外输出 `$PRO_PIXELS`(TikTok 标准 ttq 脚本 / 额外 Meta `fbq("addPixelId",id)+trackSingle PageView`, 与主像素不同才输出); pro_show.php 模板变量兜底 `isset($PRO_PIXELS)?...:''`
- 编辑器手机预览 iPhone 17 Pro Max 规格: 440px 宽(6.9" 1320pt@3x)/66px 外壳圆角+56px 内屏/钛金属渐变边框/灵动岛 128×38 悬浮(内容区顶部 66px spacer 避让)/侧边音量电源键
- reviews 评价组件: 内置台湾姓氏/地区池随机 + 手机脱敏 + "X分鐘前" 动态时间 + 评分星(支持非整数 4.6, 部分星宽度百分比)
- **验证坑: HTML 单行时 `grep -c` 只算 1 行, 统计条目用 `grep -o '关键词' | wc -l`**

## 12c. 商品页交互失效根因(Swiper 中断 ready 回调)⭐

症状: 商品页 200、渲染正常(倒计时/販賣量可见), 但点「立即搶購」/任何按钮无反应、不跳下单。curl 检查 HTML/JS 结构、静态资源全 200 都正常——**必须真实浏览器抓 console**(headless Chrome + CDP, 见 `browser-js-debugging` 技能)。

- **根因**: pro_show 的 `$(document).ready(function(){ new Swiper('.main-swiper', {...thumbs: {swiper: '.thumb-swiper'}}); ...; $cnmallOrder.on('click', showCheckout); })` —— Swiper 初始化抛 `TypeError: Cannot read properties of null (reading '$el')` → **整个 ready 回调中断** → 后面所有按钮绑定(showCheckout)从未注册 → 点击无反应
- **Swiper thumbs 时序坑**: thumbs 传**选择器字符串**时, 若缩略轮播未先初始化 → 内部访问 $el 为 null。**必须 thumb 先 `new Swiper('.thumb-swiper', ...)` 得实例, 主轮播 `thumbs: {swiper: thumbSwiper}` 传实例**
- **修复模式**: 轮播(及其他第三方库)初始化整体 try/catch + `document.querySelector` 元素存在性检查, 保证业务绑定代码必定执行
- 附带修复: `<script src="fp.min.js" onload="generateFingerprint()">` 调用了从未定义的函数(实际采集逻辑在后续 async IIFE 自行执行)→ 去掉无效 onload 属性, console 归零
- **CDP 实测确认**: 点击前后对比 `mainContent.hidden` / `checkoutContent` 可见性(页内切换不跳 URL, 别只看 location); ERRORS(0) + DOM 状态变化 = 修复完成
- 这类"页面能渲染但交互死"的问题用 CDP 一次定位(错误+行号+调用栈), 肉眼排查效率低十倍

## 12d. 下单提交不跳转/500 完整排查链(三层 bug 叠加)⭐

症状: 手机号栏红字提示、或提交后无反应/提示失败、或 500。**三层问题可叠加, 逐层排**:

**① 前端字段校验过严(卡在具体字段)**: 台湾手机规则 `/^(09|9)\d{8,8}$/` 会拦截任意测试号(如 `3132901982` 31 开头)→ 提示「請填寫正確手機號碼」卡字段。修复: 放宽为 `/^\d{8,15}$/`(纯数字 8-15 位)——**前端 pro_show.php 与服务端 order.php 的校验必须同步改**, 否则前端过了后端 500/拦截。

**② 前端提交函数依赖缺失(提交请求根本不发出)**: 商品页 `skuComponent.redirectTocamll()` 调 `layer.load()` 但页面从未引入 layer 库 → `ReferenceError` → **$.ajax 提交永不执行**(点提交显示"提交中…"后无任何网络请求)。修复: 自托管 layer 3.5.1(bootcdn 下载 layer.js + theme/default/{layer.css, loading-0/2.gif})到 `/static/assets/lib/layer/`, head 引入(在 jquery 后)。诊断关键: Network 层抓 `s=order` 请求——**0 请求 = 前端卡死, 有请求看响应**。

**③ 服务端 500: PHP Error 不被 try/catch(Exception) 捕获** ⭐: order_buy 里 `try { tg_notify_order([...]); } catch (Exception $e) {}` —— 若 tg_notify_order 参数不匹配(如函数签名要 3 参、调用只传 1 参)→ `ArgumentCountError` 是 **Error 不是 Exception → 直接 Fatal 500(空 body)**。修复: 参数给默认值 `array $pro = [], array $skuVal = []`。**教训: 改函数签名时 grep 全部调用点; 下单链路任何改动后必须服务端 POST 实测**(GET 页面拿 `csrf_test_name` + cookie jar → POST `?s=order&c=order&m=buy&mid=pro&id=61&sku=0_0&num=1&huilu=1&ccode=` 带全表单 data[name/phone/city/address...] + paytype=nopay, 期望 `{"code":1}`)。这也解释了"之前能下单、某次改动后不能"——**回查最近改动过的调用链**。

**④ head 同步脚本阻塞 body 解析(页面 200 但 body 不出)**: 远程 CDN script(lazysizes 等)在 head 同步加载, CDN 慢/被墙 → body 永不解析。修复: 本地化 `/static/js/lazysizes.min.js`(本地有副本直接换)。

## 12e. CDP 无头调试要点(页面交互问题必用)⭐

用 headless Chrome + CDP 抓 console 错误/实测点击(肉眼排查十倍效率)。完整可复用脚本: `scripts/cdp_page_probe.js`(页面状态/console 错误/点击前后 DOM 对比)。

- **Node ≥22 自带 WebSocket**, 不需要 npm ws 包; 事件用 `addEventListener`(原生 API, 不是 ws.on)
- **必须连 page target**: `/json` 列表里 `type==='page'` 的 webSocketDebuggerUrl(连 `/json/version` 的 browser 级会报 `'Page.enable' wasn't found`)
- **Chrome 对 127.0.0.1 默认 bypass 代理**(--proxy-server 指向本机端口时不生效!)→ 必须加 `--proxy-bypass-list=<-loopback>`
- headless 继承系统代理: 代理进程死了 → `chrome-error://chromewebdata/` "This site can't be reached"; 测代理可用性用 `curl -x http://127.0.0.1:<port>` 扫常见端口
- 页面就绪轮询: `document.body && document.querySelector('#app') && typeof Vue !== 'undefined'`(直连慢时轮询最长 40-60s)
- 页内切换 UI(如显示/隐藏结算区)验证: 对比点击前后 `classList.contains('hidden')`, **别只看 location.href**
- **本机到服务器网络故障时的绕行验证**: 本机 SSH(21661)→ 服务器出口。方案: 本地 Python 写 **SOCKS5 服务器**(paramiko direct-tcpip, ~50 行)+ Chrome `--proxy-server=socks5://127.0.0.1:10899` + `--proxy-bypass-list=<-loopback>`; **目标域名/IP 映射 127.0.0.1 走服务器回环**(Chrome 本地解析域名发 IP, 所以 `xeelee.top` 和服务器公网 IP 都要映射; TLS SNI/HTTP Host 不受影响)。服务器访问自己公网 IP 会绕外网路由(每请求 5s+), 回环 0.3s。

## 12f. 商品详情长图文组件化(用户纠正: 不要 HTML 文本域, 必须组件编辑器)⭐

- **用户偏好铁律**: 商品详情编辑**必须做成组件化编辑器**(组件库/手机预览/属性面板), 给 HTML textarea 会被否(「不要这样的,做成那种自定义模块的」)。投手看到的是落地页, 商品概念退居幕后。
- **架构**: `dr_pro.detail_json`(组件数组 `[{type, props}]`)+ `lib/detail.php` 双函数:
  - `detail_components_to_html($comps)` — PHP 前台渲染(与编辑器 JS `renderComp()` 双端同一 schema)
  - **组件集(9 → 18 个, 四组, 用户要求\"落地页组件和商品页组件全部合并\"后)**: 基础=title/text/image/fullimg/video/button; 营销=countdown/reviews/product/marquee; 内容=card/label/faq/form/footer; 装饰=divider/space/notice。新增 9 个的要点:
    - **button**: text/link/bg/color/size/radius/**full(通栏 checkbox)** → `<a>` 样式渲染
    - **fullimg**: src/link(可点击跳转)
    - **product(商品卡)**: proid 下拉选商品(**pro_detail_index 查全部启用的 dr_pro 传模板 → `window.PROS` JS 数组**; renderProps 的 select 分支对 proid 用 PROS 生成选项, 其他 select 用 f.o); 前台 `detail_render_product()` 查库渲染真实商品(图/标题/售价/划线价/「立即搶購」按钮链商品页), 商品不存在显示占位「商品 #N 不存在或未发布」——**验证时 grep \"商品 #N\" 应为 0(渲染了真实商品=成功)**
    - **marquee(滚动公告)**: text/bg/color/speed → `<marquee scrollamount>`(最简滚动实现)
    - **card/label/footer**: 图文卡/圆角标签/底部版权
    - **faq**: items 数组, 属性面板用 **textarea 每行 `问题|答案`**, `setFaq(raw)` 按 `|` 解析成 `[{q,a}]`(FIELDS 加 `t:'faq'` 类型)
    - **form**: text/bg/pid → 姓名+電話表单,**前台提交依赖商品页全局 `lpForm()`**(fetch POST `?s=page&c=lead` 落 dr_page_lead, 成功提示+reset)——**pro_show.php 底部必须注入 lpForm 函数**, 否则表单提交报错
    - **保存白名单($allowed)必须同步加全部新类型**, 否则保存被静默过滤
    - **倒计时**: end 截止时间 + bg/color/text, PHP 渲染内联 `<script>setInterval(...)</script>` 每秒 tick(span id 用静态变量 `$cdIdx` 递增保证多实例唯一, 结束显示 `N天HH:MM:SS`); **最新评价**: rating(支持 4.6 非整数, 星级 round 取整)/count(2-20)/product, PHP 与 JS **各自维护台湾地区池(20 区)+姓氏池(20 姓)随机生成**, 手机脱敏 `09** ***xxx`, 时间 `X分鐘/小時前` 动态, 底部「— 以上為近期訂單真實反饋 —」
  - `detail_html_to_components($html)` — 旧 HTML 长图文自动迁移(按 `<p>` 切分, img 提取成 image 组件 + strip_tags 文本成 text 组件)
  - pro_show 渲染优先级: detail_json 有 → 组件渲染; 无 → content HTML 兜底。保存时**同步写 detail_json + content(渲染后 HTML)** 兼容旧逻辑
- **迁移触发**: `pro_detail_get` 里 detail_json 空且 content 有 → 自动解析入库(幂等, 下次直接读)
- **编辑器页面** `templates/admin_pro_detail.php`: 三栏(组件库 7 组件/手机预览/属性面板)+ 顶部工具条(保存/返回); 入口: 落地页管理 → 编辑弹窗「🧩 用組件編輯器編輯詳情」按钮
- **坑: lib 里用公共函数必须先自包含**——detail.php 用了 page.php 模块的 `h()` → `Call to undefined function` Fatal(pro.php 加载时 page 未必加载)。lib 文件自带局部转义函数(如 `dh()`)
- **坑: 迁移正则无捕获组** — `preg_match_all('/<img\b[^>]*>/i', $seg, $im)` 必须用 `$im[0]`(不是 `$im[1]`, 后者恒空 → 图片全丢只剩 text)
- **坑: 保存接口测试传单对象**(`{"type":"title"...}` 非数组)会被 array_filter 当合法组件保留 → detail_json 变关联对象 → 渲染全跳过 → **content 被覆盖为空串**(商品页详情消失)。保存前必须 `array_values` + 校验每项是 `{type, props}` 结构; 测试传数组 `[{...}]`
- **恢复铁律**: content 被覆盖后原 HTML 只在迁移/恢复脚本里有副本——测试保存前先备份 content, 或用独立恢复脚本(含原 HTML 常量)还原, 别在测试脚本里"恢复"成同样的测试内容
- product_get 是**显式字段列表**(非 SELECT * 直返)——加新列后记得在 json 输出里补字段
- 后台编辑弹窗保存(product_edit)**不要再带 content 字段**(详情由组件编辑器单独管理), 否则弹窗保存会覆盖组件渲染结果

## 12g. 新建落地页 = 添加商品(单页 COD 产品模式)⭐

- **用户提出**: 商品就是落地页, 那「新建落地页」就是完整添加商品——后台商品概念完全退居幕后, 落地页管理是唯一入口
- **按钮文案(方案A 后)**: 「+ 新建卖货页」(商品即落地页, 含下单); 曾叫「+ 新建落地页」, 砍掉自定义页后统一为卖货页
- **新增弹窗完整表单**: 落地页标题(商品名)/ Slug / 主图本地上传 / 售价 / 划线价 / **库存** / ☑ 创建后进入详情组件编辑器
- **product_add 支持 qty**(写进 sku_json value['0_0'].quantity, 不再硬编码 1000)
- **创建后跳转**: doAdd 成功 → checkbox 勾选 → `location.href = '/index.php?s=admin&c=pro_detail&m=index&id=' + j.id`(直接搭详情)→ 否则 alert + reload
- 投手完整流程: 新建落地页(标题/主图/价格/库存)→ 自动进详情组件编辑器 → 保存 → 复制链接投放; 以后改: ⋯ → 编辑
- 底层: 一个落地页 = 一个 dr_pro 商品(标题/价格/库存/详情全落库), 前台商品页即时可访问
- **旧表补列铁律**: 服务器旧库缺新列时(`dr_fb_event` 缺 `capi_status` 等)→ db.php 初始化 `try { $pdo->exec("ALTER TABLE ... ADD COLUMN ..."); } catch (Exception $e) {}` 容错补列(无 IF NOT EXISTS 语法, 已存在会抛错正好吞掉); 部署后访问一次页面触发建列, 再用 PRAGMA table_info 验证

## 12h. 后台简体 / 前端繁体(用户 UI 偏好)⭐

- **用户偏好铁律**: 后台所有界面(菜单/按钮/表单/提示/编辑器)**简体中文**; 前端(商品页/下单页/成功页)**保持繁体**(客户看到的)。投手/自己用后台, 客户看前端。地区名等**业务数据不转**(南投縣/高雄市 保持原样, 是数据不是 UI)
- **批量转换法**(后台文件多时): 词级映射表(数百常用词: 訂單→订单/編輯→编辑/詳情→详情/組件→组件/落地頁→落地页/保存詳情→保存详情…)+ 字级映射表(簡繁差異特徵字: 裡與並為於個這時後對從麼…→简体)+ 先词后字两次 replace
- **扫描验证**: 特征字清单遍历文件, 剩余命中逐条看上下文——**繁简同形字(黑/隆/单/录)和地区数据示例是正常残留, 不是漏转**
- **部署验证**: 登录后台逐页 grep 简体关键词(落地页管理/新建落地页/保存详情/订单管理…)确认命中; 302 是登录后正常重定向, 用 `-L` 跟随
- 前端文件(pro_show/page_show/pro.php/order.php/page.php)与数据库**绝不参与转换**

## 12i. 新建落地页 slug 自动生成(投手零门槛)⭐

- slug = 页面网址尾巴(`https://xeelee.top/<slug>`)。**投手不用理解 slug——留空自动生成**
- product_add: slug 为空 → `do { $slug = bin2hex(random_bytes(16)); 查重 } while(重复)`(32 位 hex 唯一); 必填校验只剩标题
- 前端: 字段改名「页面网址(选填, 留空自动生成)」+ placeholder「留空自动生成, 如 c7f39f8317」+ 🔄 随机按钮(清空输入)+ 说明行「网址尾巴, 如 xeelee.top/<这里>」

## 12j. 后台列表 UI 迭代坑(操作列/弹层/手机预览)⭐

用户连续截图反馈 UI 细节时的三类高频坑(全部实测修复):

- **操作列横向放不下**: 3 个按钮(取消发布/复制链接/⋯)总宽 >220px 溢出表格右缘。修复: 精简为 2 个紧凑按钮 `[🔗 链接] [⋯]`(height 24px/padding 0 8px/字号 11.5px, 总宽 ~90px), **取消发布/编辑/详情组件/像素设置/删除全部收进 ⋯ 下拉菜单**(取消发布按状态显示 ✕取消发布/✓发布, 红色 danger 类)
- **⭐ 弹层被表格容器裁剪(「被条挡住了」)**: `.table-wrap{overflow:hidden}`(圆角+阴影裁剪)会把 absolute 定位的 ⋯ 下拉菜单切掉——菜单根本看不见。**修复模式: 弹出层用 `position:fixed` + 打开时 `getBoundingClientRect()` 计算视口坐标**(右对齐按钮 `left = min(r.right - mw, innerWidth - mw - 8)`, 底部空间不足 `top + 180 > innerHeight` 时向上弹 `top = r.top - 180 - 4`), z-index 100。**任何圆角卡片容器内的弹出层都必须 fixed 定位, 别用 absolute**
- **手机预览顶部白条**: 原结构 `.phone-bar`(34px 白底)+ `.phone-notch` 居中 → 灵动岛上方一条白色状态栏条, 不真实。修复(最终形态): **去掉 phone-bar, notch 改 `position:absolute; top:8px; left:50%; transform:translateX(-50%)` 悬浮在 `.phone-inner` 顶部, 内容区 `.phone-screen` 加 `padding-top:42px` 避让**——灵动岛悬浮在内容上, 像真实 iPhone(与 page_editor 的 66px spacer 方案同理, 白条必须消除)
- **控制器方法名不统一**: 删除接口叫 `product_delete` 但前端 POST `m=del` → 「方法不存在」{code:0}(不报 500 但操作静默失败)。改接口名/新建接口后 grep 前后端方法名一致; 用后台 API 测试删除/状态类操作前先 `grep "function product_" modules/admin.php` 确认
- **按钮类 UI 验证**: 上传后 `grep -c` 关键类名/文案(op-link/more-btn/取消发布)确认渲染; 弹层交互必须真浏览器点(CDP 或人工), 静态 grep 看不到裁剪问题

## References

- `references/cloak-risk-control.md` — 斗篷 11 规则引擎 + Meta CAPI 完整实现与测试方法
- `references/admin-module-pattern.md` — 后台占位菜单转真模块四件套(菜单/控制器/模板/验证) + array_values PDO 坑, 区域管理 15483 条实战
- `references/tg-order-notify.md` — Telegram 订单通知完整模式(lib 封装/后台三方法/getUpdates 自动 chat_id/BotFather 注册流程/下单挂钩)
- `references/domain-bind-sudoers.md` — 后台一键域名绑定: sudoers 白名单模式(PHP exec→sudo -n)/vhost 双文件/certbot webroot expand/DNS 预检/探针验证/实测结果
- `references/page-builder.md` — 组件化落地页编辑器: 16 组件 schema/双端渲染(JS 预览 + PHP 前台)/原生 JS 编辑器三栏布局/表单线索/安全校验/实测结果
- `references/backend-modules.md` — 后台功能扩展总览(与上述 references 部分重叠, 含独有的: 商品=落地页融合列表/多平台像素 fbpixel/上传安全链/17 Pro Max 预览/评价组件)
