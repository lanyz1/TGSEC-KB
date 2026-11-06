---
name: xunruicms-recon
description: "迅睿CMS系PHP商城逆向: 路由/下单/模板API。触发:迅睿CMS/长安COD, csrf_cookie_name。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# XunRuiCMS(迅睿CMS)系站点逆向

迅睿CMS(基于 CodeIgniter 3.x)及其二开系统(典型: 长安COD货到付款商城)的识别、路由枚举、API 逆向方法论。前端为服务端渲染 HTML + 内联 Vue2, 业务 API 走 query-string 路由, 无独立 SPA bundle 可挖 —— 信息全在 HTML 内联 JS 与接口响应里。

## When to Use

- 目标为 PHP CMS 商城/落地页, 响应含 `csrf_cookie_name` cookie 或 `index.php?s=模块&c=控制器&m=方法` 路由
- 页面注释含"长安COD"/"COD系统搭建", 静态资源在 `staticapac.rdian.net`, 错误页链接 `v1v1.cacod.net`
- 需要从服务端渲染页提取 SKU/商品数据、重建下单接口、导出地区库

## 1. 框架识别(5 秒)

- `Set-Cookie: csrf_cookie_name=<32hex>` → CodeIgniter 3.x(XunRuiCMS 4.x 基底)
- 路由 `index.php?s=<mod>&c=<ctrl>&m=<method>`(query-string 路由)
- `<script src="/static/assets/js/cms.js">` + JS 内 `dr_` 前缀函数(dr_lang/dr_strtotime/dr_tips)= XunRuiCMS 官方前端库
- 页面注释 `<!--使用长安COD系统搭建，了解更多+v:xxx-->` = 长安COD 二开
- 模板错误页"点击返回上一页"链接 `v1v1.cacod.net` = 系统商官网痕迹(常已 404)

## 2. 模块/路由枚举

```bash
# 模块探测: 非404即存在(s=weblog 无 c/m 直访 = 默认控制器)
for m in pro order pay member api weblog ip_cz news home cart; do
  curl -s -o /dev/null -w "$m %{http_code}\n" "https://T/index.php?s=$m&c=index&m=index"
done
# 控制器方法探测: 200=存在(业务错误也算存在), 302/404=不存在或需登录
for m in buy buysuccess pay index my show; do
  curl -s -o /dev/null -w "$m %{http_code}\n" "https://T/index.php?s=order&c=order&m=$m"
done
```

长安COD 典型模块: `pro`(商品)/`order`(下单)/`pay`(支付)/`member`(会员, 常显示"系统没有可注册的用户组"= 注册关闭)/`api`(标准API)/`weblog`(行为埋点)/`ip_cz`(FB CAPI 代理)/`news`(文章, 常空)。

## 3. CSRF 机制(下单必需)

- 页面隐藏字段 `csrf_test_name` 的值 = Cookie `csrf_cookie_name` 的值(每次 GET 刷新)
- 所有 POST 必须携带 csrf_test_name 且与当前 cookie 匹配
- **每次 POST 前先 GET 页面刷新 cookie+token**(脚本模式: 先 curl GET 拿 CSRF, 同 cookie jar 再 POST)
- 下单接口响应可能返回 `res.token`(name/value)供前端更新表单字段

## 4. COD 下单链(核心业务)

```
POST /index.php?s=order&c=order&m=buy&mid=pro&id=<商品ID>&sku=<SKU>&num=1&huilu=<汇率>&ccode=<国家码>
Content-Type: application/x-www-form-urlencoded
```

- GET 参数: `mid`=模块目录(pro), `id`=商品ID, `sku`=SKU组合键, `num`=数量, `huilu`=汇率, `ccode`=地区码(tw)
- POST 必填: `csrf_test_name`, `paytype=nopay`(货到付款), `data[name]`, `data[phone]`(台湾 09xxxxxxxx 强校验), `data[city]`(region_id), `data[address]`
- 其余 data[] 字段: `huobi`(NT$)/`abchanpin`(落地页URL)/`laiyuan`(来源)/`gjcs`/`wuliufangshi`(物流: 1宅配 2=7-11 3=全家 4=香港顺丰 5=黑猫)/`pydqyf`(运费)/`fingerprint`(浏览器指纹)/`timezone` + 反作弊 `dr_paste_count`/`dr_has_large_paste`/`dr_form_fill_time`/`dr_total_input_count`/`dr_page_stay_time`/`dr_form_source`
- 成功: `{"code":1,"msg":"success","data":{"url":"...buysuccess...&ordata[sn]=H2608191945496097..."}}`; 前端 2s 后跳 data.url
- **脚本验证(Windows curl)**: 同一 cookie jar 必须 `-b` `-c` 同读同写; CSRF 字段从同一次 GET 响应 HTML 提取; 响应的 `data.url` 是 JSON 转义(`\/`), 用 `json.loads` 解析, 正则提取会拼出坏 URL(HTTP 000)。完整可跑脚本: `scripts/e2e_buy_test.sh`
- 订单号格式: `H` + yymmddHHMMSS + 4位随机
- 错误: "付款方式不存在"= 缺 paytype; "Submit too fast"= 频率限制(新 session 重试常成功); 表单错返回 `data.field` 定位字段
- `buysuccess` 页: Nuxt SSR 渲染订单确认页, 订单数据明文走 GET(知道订单号即可查看)

## 5. 模板渲染 API(信息泄露/页面重建)

```
GET /index.php?s=api&c=api&m=template&name=checkout.html[&id=&mid=]
```

- 渲染指定模板; **未配置的模板名全部 fallback 到默认信息页(返回内容完全相同)= 假阳性**, 只有内容不同的才是真实模板
- 配合下单流程可拿到成功页/确认页模板源码(页面重建金矿)

## 6. 地区联动数据导出(全量)

```
GET /index.php?s=api&c=api&m=linkage&code=tw         # JS变量: var linkage_tw=[{value,label,children}]
GET /index.php?s=api&c=api&m=linkage_ld&mid=order&code=tw[&parent_id=N]  # JSON: {data:[{region_id,region_code,region_name}]}
```

- code: `tw`/`tw711`(7-11门市明细)/`twqj`(全家门市)/`twhls`(黑猫)/`hksf`(香港顺丰)/`hk`/`sg`/`my`/`us`; `cn` 为空(不配送大陆)
- 直接全量抓取即可重建前端地区选择器

## 7. 商品枚举(采样即可)

```
GET /index.php?s=pro&c=show&m=index&id=N    # 200 且 >5KB = 商品页
```

- 商品页结构: 服务端渲染 HTML + 内联 Vue2 app + `skuData` JSON(`group`/`name`/`image`/`value`/`demoname`)
- SKU key = 组ID_选项ID 下划线连接(如 `0_0`); `value` 含 price(售价)/yprice(划线价)/quantity/sn
- **用户偏好: 采样一部分够用就行, 不全量扫完**(用户多次纠正勿过度枚举)

## 8. 统计/广告埋点

- `s=weblog` JSONP: `?s=weblog&url=...&cpu=&stayTime=&event=view30|view60|view90|hidden|addtocart|purchase|contact|phonepaste|namepaste&uid=&thumb=&citycode=...`(行为追踪, 服务端落库; uid=站点ID, thumb=模板ID)
- `s=ip_cz&c=home&m=dr_facebook` POST sendBeacon JSON: FB Conversion API 服务端代理(多像素 Purchase 事件), 支持 TikTok/Snap/Kwai/Taboola/Google 多平台
- `api/module/hits`: `?s=api&c=module&siteid=1&app=pro&m=hits&id=N` → JSONP `callback({"code":1,"msg":<浏览量>})`

## 9. 后台入口

- XunRuiCMS 默认 `admin.php`; 长安COD 二开常改自定义文件名
- 子域全返回 530(wildcard DNS)= 子域未配置; 真后台常在独立域名或隐蔽路径
- 探测判读: 404 且 9 字节 = 标准 404; 404 且 7KB+ = 页面模板 404; `302 → /404.html` = 通用 404 跳转
- 后台未找到时应诚实收尾并建议用户自查(站主知道自己后台域名), 不硬猜

## 10. 重建版本地验证与交付(逆向→复刻闭环)

重建"一模一样"本地版(PHP 8 + SQLite 等)后, 验证与交付流程:

1. **启动**: `D:\tools\php83\php.exe -S 127.0.0.1:8080`(不加 `-t`, 当前目录即 docroot); bash 里用子 shell `(cmd &)` 或 terminal background=true(裸 `&` 会被拒绝)
2. **存活检查**: `tasklist //FI "PID eq <pid>"`; curl `-s -o NUL -w "%{http_code} %{size_download}"` 商品页应 ~132KB(与线上 134KB 保真)。首次请求 size 0 多为启动竞态, 等 1-2s 重试即可
3. **验证矩阵**(按序): 商品页 slug/标准路由 200 → hits JSONP → **端到端下单**(跑 `scripts/e2e_buy_test.sh` 全自动)→ 后台登录搜订单号确认落库
4. **演示打开(用户要求"谷歌浏览器打开"时)**: 直接 bash 调用 `"C:/Program Files/Google/Chrome/Application/chrome.exe" "url1" "url2"`(URL 加双引号, 可一次开多标签); **禁用 `cmd //c start chrome <url>`**——URL 里 `?s=admin&c=index&m=index` 的 `&` 会被 cmd 当命令分隔符截断成三段。登录成功的验证信号: 标签标题从"管理后台"变为"订单管理"(已跳转列表页)
5. **打包交付**: `cd 上级目录 && tar -a -cf "桌面包.zip" rebuilt`, 复制 zip 到桌面; 汇报验证矩阵 + 交付路径 + 管理员账号

## Pitfalls

- **原生 Windows curl 三坑**: ① `-o /dev/null` 报 exit 23 — 用 `-o NUL`; ② `/tmp/xxx`、`/tmp_local_x` 都是 MSYS 虚拟路径(写完读不回来), 输出写当前目录相对路径; ③ 中文路径写不进(`-o /d/渗透/x` → No such file), 先下载英文目录再 cp
- **CSRF curl 流程**: jar 必须 `-b` `-c` 同文件读写——只 `-c` 不带 `-b` = 服务端认为无 cookie 每次发新 token, 字段/cookie 必然不一致; 失败特征 JSON `{"code":0,"msg":"非法请求(CSRF校验失败)"}`。HttpOnly cookie 在 Netscape jar 里行首带 `#HttpOnly_` 前缀, grep 比对 cookie 值时注意; 下单成功后响应 `token` 字段是刷新后的新 CSRF, 后续 POST 要换
- JSONP 接口响应形如 `callback({...})`, 解析时剥掉前缀
- "Submit too fast" 可能只是瞬时限速: 新 GET 刷新 CSRF + 换 cookie session 后重试常成功
- SKU/商品数据全在服务端渲染 HTML 内联 JS 里; 外部 JS(cacod.js/va22.js/cms.js)只是公共库(Vue2.7/Vant/Tailwind/XunRuiCMS官方库)——业务逻辑别去压缩 JS 里找
- 测试下单会真实落库(站长后台可见订单)——用户自站可接受, 但控制测试订单数量
- 会员模块"系统没有可注册的用户组"= 商家关闭注册, 纯 COD 无会员体系, 别浪费时间打注册面

## Verification

- [ ] 识别出框架(CI3/XunRuiCMS/长安COD)与模块清单
- [ ] 下单链打通: 拿到 code=1 + 订单号
- [ ] 地区库/商品页/SKU 数据导出
- [ ] 摸清 CSRF 刷新机制并复现

## References

- `references/zengda-cod-case.md` — zengda.shop(长安COD)实战: 完整接口契约/响应格式/SKU结构/订单流程/资产清单
- `references/rebuild-notes.md` — 重建版(自建 PHP8+SQLite)技术笔记: 路由 {c}_{m} 命名坑/CSRF复刻/SQLite统计SQL/城市名映射/后台UI重设计位置
- 重建版**生产部署上线**(服务器/域名HTTPS/斗篷/像素/上线清单): 见 `cod-ecommerce-launch` 技能。关键: CentOS7 老 SQLite(3.7.17)无 UPSERT, 一律 INSERT OR REPLACE; 批量同步代码排除 config.php(防本地配置覆盖服务器密码)
