---
name: cod-shop-ops
description: COD商城系统后台/组件编辑器/前台迭代运维。触发 落地页/组件编辑器/投手工作台/改价不同步。
---

# COD 商城系统运维迭代(后台/组件编辑器/前台同步)

PHP+SQLite 单页 COD 系统(马总COD/zengda/长安COD系,商品=落地页、detail_json 组件化、投手工作台)的迭代运维。
本技能沉淀**通用 bug 模式**——任何组件化编辑器 + sku_json 双写结构的系统都会踩的坑。

## 核心架构(先理解再动手)

- **商品=落地页**:dr_pro 一表两用;url_slug 唯一;detail_json(组件JSON)优先渲染,content(HTML)兜底
- **组件编辑器**:前端 JS 渲染(renderComp/renderProps)+ 后端 PHP 渲染(detail_components_to_html)双端一致;保存时 JSON 白名单校验
- **sku_json 双写**:dr_pro 有 title/thumb 字段,sku_json 里还有 group/name/image/thumb/yunfei——**改任何一处必须同步另一处,否则前台部分位置显示旧值**

## 高频 Bug 模式(全部实战踩过)

### 1. 硬编码业务值 → 后台改价/改名前台不同步
模板里写死 `value:'986'`、`<title>【猛豹久硬挺】</title>`、像素 `content_name:'...'` → 后台改了前台部分位置不变。
**修法**:全链路 grep 硬编码值 → 全部改 `$sku['value']['0_0']['price']` / `$pro['title']` 动态取。改价后验证:前台显示/结算 priceshow/像素 value 三处。

### 2. 渲染函数 `for (var i)` 污染索引参数(「模块串行」)
`renderComp(c, i)` 内 `for (var i = 0...)` 覆盖参数 i → 该组件包裹层的 selectComp(i)/moveComp(i)/删除索引全部错乱。
**修法**:循环变量一律 `for (let i...)`(块级作用域)。排查:grep `for (var i` 在渲染函数内。

### 3. oninput 全量 render → 输入框重建 → 中文输入法/光标丢失
属性面板 oninput → setProp → render()(预览+面板全重建)→ 输入框销毁,中文只能打一个字。
**修法**:render 拆分为 renderScreen()(只刷预览)+ renderProps();oninput 只调 renderScreen,onchange(失焦)才 syncProps() 重建面板。

### 4. 新增 SKU 档保存丢失
`product_edit` 里 `isset($sku['value'][$key])` 检查 → 新加的档在旧 sku 不存在被跳过。
**修法**:不存在自动创建;同时提交档键集**移除未提交旧档**(删除生效)+ **键重排 0_0/0_1/0_2**(保证与 name/image 数组索引一致);前端新档 key 取「最大序号+1」防撞号。

### 5. POST 参数顺序 bug
多档解析循环按 POST 顺序,`image_0_0` 若在 `price_0_0` 前到达,条目未创建 → isset 失败。
**修法**:无依赖字段(如 image)分支也要独立创建条目,不依赖其他字段先到。

### 6. Number(undefined) = NaN
运费等联动字段初始未定义 → `Number(skuData.yunfei)` = NaN → 运费/合计全 NaN。
**修法**:显示处 `Number(x || 0)` 兜底 + mounted 初始化默认 0 + 下单提交链路同步兜底。

### 7. 改标题/主图不同步 sku_json
`product_edit` 只 UPDATE dr_pro.title → sku.group/name 还是旧名。**标题/主图变更必须同步 sku['group']/['name']/['thumb']/['image']**。

### 8. fail2ban http-get-dos 误封后台
filter 匹配所有 GET/POST + maxretry=60/5min → 后台频繁操作(>60 次/5分钟)被误封 →「无法访问此网站」。
**修法**:jail.local 的 http-get-dos maxretry 提到 300、bantime 降到 300;`fail2ban-client set <jail> unbanip <ip>` 解封;常用 IP 加 ignoreip。

### 9. .htaccess 旧硬编码路由
单商品时代 `RewriteRule ^([a-f0-9]{32})$ index.php?s=pro&c=show&m=index&id=61 [L]` → 多商品化后所有 32 位 hex 新链接全指向旧商品(id=61)!
**修法**:多商品化必查旧 rewrite;32 位 hex 应转发到 `index.php` 让 route_by_slug 按 slug 查。

### 10. 组件动画用 JS 驱动,不依赖 CSS keyframes
CSS `@keyframes` + `animation:` 在部分浏览器/缓存组合下不生效(用户实测不动)。
**修法**:JS setInterval(30ms 位移 1px)+ 双份内容 + `Math.abs(y)>=half 归零` 无缝循环 + 悬停暂停(mouseenter clearInterval/mouseleave 重启)。
**无 CDP 验证动画**:`chrome --headless=new --proxy-server=socks5://127.0.0.1:10808 --virtual-time-budget=6000 --dump-dom URL | grep translateY` —— transform 变化即动画在跑。

### 11. 组件图片隔离原则(用户明确要求)
「在哪里上传的图片,就显示在哪里」——任何图片组件上传只影响该组件;商品主图(thumb)唯一入口=商品设置弹窗。**不要在 pro_detail_save 里做 mainimg→thumb 自动同步**(会连带改主图)。

## 投手工作台 UI 规范(用户偏好)

- 后台简体、前端繁体;商品页移动优先(PC 端 560px 居中自适应)
- 组件编辑器:手机预览**固定 844px(9:19.5 正常手机比例)**,内容区内部滚动,不无限拉长;布局**贴合左侧侧边栏**(覆盖 .content 的 padding/max-width)
- 新建落地页 = 完整商品表单(标题/网址自动生成/多 SKU 规格名+缩略图+价格+库存/运费);创建后进组件编辑器(默认整套组件配置,不空白)
- 主图是「页面组件」组里的一个组件;所有带文字的组件文字全可编辑(标题/动作/尾注/placeholder 全参数化)
- 商品设置弹窗:规格名/缩略图/多档价格/运费每页独立
- 前端结算:规格选择显示缩略图(images[gid][optionIndex]);运费=商品固定运费(地区费可选覆盖)

## 验证方法论

- 部署后必须**服务器本地 curl 验证渲染**(`curl -sk https://127.0.0.1/<slug> -H 'Host: 域名'`),grep 关键标记
- 改数据后验证「最终业务状态」:数据库值 vs 前台 HTML vs 编辑器回显 三处一致
- 清理测试数据(创建的商品记得删,方法名 product_delete)
- 本机浏览器工具(CDP/browser_exec)走代理可能超时——优先服务器 curl + chrome --dump-dom

详细案例见 references/editor-bug-patterns.md
