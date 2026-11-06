---
name: webapp-rebuild-from-recon
description: "重建丢失源码的Web应用: 源码包+架构+API文档。触发: 恢复源码, 源码丢了, 复刻系统, 一模一样。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# 从 Recon 逆向重建 Web 应用(源码恢复/复刻)

用户丢失源码时,从线上站点完整逆向重建:前端保真 + 后端行为等价。交付 = 可运行源码包 + 架构分析 + API 文档(用户画像:破解/渗透成功后常要求"一模一样"复刻部署)。

## When to Use

- 用户说"这是我自己的网站,源码丢了/被删了,帮我恢复"
- 逆向/渗透完成后的"交付源码包"阶段(用户要能自己跑起来)
- 需要把黑盒站点还原成可部署的同构系统

## 工作流

1. **完整 recon 先行**(见 spa-frontend-recon / spa-api-discovery / web-cms-pentest):
   - 全量抓页面(商品/落地页/成功页/404/信息页)+ 内联 JS + 外部 JS/CSS + 数据 JSON
   - 枚举并**实测每个接口**(GET/POST 都 curl 一把,拿真实请求/响应),产出 API 契约
   - 识别框架指纹(路由格式/CSRF 机制/框架特征,如 XunRuiCMS `index.php?s=模块&c=控制器&m=方法`)
   - **枚举/扫描适可而止**:用户偏好采样够用即可,不要全量扫完(如商品列表扫一段确认结构就停)
2. **定技术栈**:优先**原生 PHP8 + SQLite**(零依赖,`php -S` 即可跑);若目标是开源框架二开,可模拟其路由格式保 URL 兼容
3. **实现后端**:路由分发 → 每个接口按契约实现 → 推断建表(表名对齐线上特征,如 dr_*)→ seed 数据(注意**线上 API 参数里的 id 要与 seed 一致**,如接口查 id=61,自增成 1 会查不到)
4. **前端保真**:抓到的 HTML 转 PHP 模板,动态数据 PHP 注入;静态资源 CDN 统一本地化(含站内相对路径 `/static/xxx` 与绝对 CDN URL 两种都要处理)
5. **数据资产导入**:地区库/字典从线上抓的 JS 文件解析入库(JS 树 → 扁平表,记 parent_id,两个接口格式可互相支撑)
6. **端到端验证**:每个接口 curl 实测 + **完整业务链路走通**(如下单→订单号→成功页),中间接口 200 不算完成
7. **打包交付**:源码包 + README + API 文档 + 部署说明(nginx/Apache rewrite 规则,伪静态如 `/slug` → index.php)

## 环境准备(Windows)

```bash
# PHP Windows 版(windows.php.net 302 到 downloads.php.net)
curl -L -o php.zip "https://downloads.php.net/~windows/releases/php-8.3.33-nts-Win32-vs16-x64.zip"
# php.ini 启用: extension=sqlite3 / pdo_sqlite / mbstring / curl / gd
# 本地跑:
D:/tools/php83/php.exe -S 127.0.0.1:8080 -t <站点目录>
# php -S 直接 serve 静态文件 + 把路由请求交回 index.php
```

## Pitfalls(实测)

- **HTML→PHP 模板转换用脚本做,转换后必须 `php -l` 验证**:
  - 子串碰撞:`tcskuData: {` 含子串 `skuData: {`,直接 `str.find` 会替换错对象 → 用正则 `(?<!tc)skuData: {` + 括号深度配对
  - 正则替换生成 PHP 代码时会产生 `$pro[\'id\']` 反斜杠残留 → 只在 `<?php ... ?>` 段内清理反斜杠,**别动 JS 里合法的 `\'` 转义**
  - 模板内嵌 PHP 变量(meta og:title 等)用 `json_encode()` 输出,注意 HTML 属性引号
- **路由命名**:`s=模块&c=控制器&m=方法` → 模块文件 `modules/{s}.php`,函数名 `{c}_{m}()`(如 c=show&m=index → `show_index()`,不是 `pro_show()`);c 缺省时 c=模块名;写错名字会"方法不存在"
- **JS 变量文件解析**:`var linkage_tw =[{...}];` 等号后可能无空格 → 正则 `var \w+\s*=\s*(\[.*\]);`
- **CSRF 复刻**:对齐目标行为(cookie+字段双校验,POST 成功后刷新 token);下单类接口防刷保留(目标限速,重建也限)
- **Windows 原生 curl 写中文路径失败**(`D:\渗透\...` No such file)→ 先下到英文 ASCII 路径再 cp
- **订单/业务数据走明文 GET 的复刻**:参数格式(如 `ordata[sn]=`)要与线上一致,前端 JS 依赖该格式跳转

## Verification

- [ ] 全部页面模板可渲染(商品页/成功页/信息页/404)
- [ ] 每个 API 契约接口 curl 实测与线上响应结构一致
- [ ] 完整业务链路端到端走通(下单→订单号→成功页显示)
- [ ] 静态资源全部本地化无外链(或明确保留的 CDN 白名单)
- [ ] 交付含 README + API 文档 + 部署说明

## References

- `spa-frontend-recon/references/xunruicms-cod-zengda.md` — zengda.shop(长安COD/XunRuiCMS)全站逆向+重建完整案例:API 契约、SKU 结构、地区库导入、表结构推断、重建坑
- `spa-frontend-recon` / `spa-api-discovery` — recon 前置方法论
