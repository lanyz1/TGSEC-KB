# 多商品化 + 投手工作台重做(COD 单页系统迭代实战)

本文件记录把单商品模板改造成「多商品落地页 + 投手自助工作台」过程中的关键坑与模式, 全部来自生产实测(马总COD/xeelee.top)。

## 1. .htaccess slug 硬编码劫持(重大)⭐

**症状**: 用户新建落地页后打开自己的链接, 却显示旧商品(61)的内容——浏览器标签/标题/轮播全是旧商品, 编辑器里却是自己的页面, 前后对不上(用户:「为什么新建的商品也是显示这个」)。

**根因**: 单商品时代伪静态规则写死了转发目标:
```apache
RewriteRule ^([a-f0-9]{32})$ index.php?s=pro&c=show&m=index&id=61 [L]
```
所有 32 位 hex slug(新建商品自动生成的网址)全部被转发到商品 61。只有 61 自己的短 slug 不受影响。

**铁律**: slug 路由必须动态。修复:
```apache
RewriteRule ^([a-f0-9]{32})$ index.php [L]
```
→ router() → route_by_slug: 按 slug 精确查 dr_pro(status=1), 查不到再查 dr_page, 都没有才 404。

**预防**: 上线/改版前 `grep -n "id=" .htaccess` 找硬编码 ID; 任何"单商品时代"写死的规则都要审查。
**验证**: 新建商品 → `curl <新slug> | grep -oE '<title>[^<]*'` 应等于自己的标题。

## 2. title / 像素 content_name 硬编码商品名

**症状**: 所有商品的浏览器标签都叫【猛豹久硬挺】; 广告平台(ViewContent)上报的商品名/价格全部是旧商品的。

**位置**: pro_show.php 两处写死:
1. `<title>【猛豹久硬挺】：壯陽補腎神藥</title>`
2. `fbq('trackSingle', ..., 'ViewContent', { content_name:'【猛豹久硬挺】...', content_ids:[...], value:'986' })`

**修复**:
```php
<title><?php echo htmlspecialchars($pro['title']); ?></title>
// 像素:
content_name:'<?php echo htmlspecialchars($pro['title']); ?>',
content_ids:['<?php echo htmlspecialchars($pro['title']); ?>'],
value: '<?php echo htmlspecialchars($sku['value']['0_0']['price'] ?? ''); ?>'
```
模板里 `$sku` 已由 pro.php view 传入, 不需要新变量(先 grep 模板可用变量, 别急着加传参)。

**通用教训**: 多商品化改造 = 全站 grep 商品名/旧 ID 硬编码(title/meta/像素/重写规则/推荐位), 逐处参数化。

## 3. 新建商品自动写入默认完整页面配置

**问题**: 新建后进编辑器是空白(即使 get 接口会自动补默认头部, 用户仍然「一脸懵」)。

**方案**: product_add 创建后立即落库默认配置:
```php
require_once __DIR__ . '/../lib/detail.php';
$dpro = ['id' => $newId, 'title' => $title, 'thumb' => $thumb, 'sku_json' => json_encode($sku, JSON_UNESCAPED_UNICODE)];
$default = detail_default_header($dpro);          // swiper(有图时)+proinfo+buybtn+trust+ticker
$default[] = ['type' => 'text', 'props' => ['text' => '👆 这是你的落地页! 点上方组件可在右侧编辑…', 'align'=>'left', 'size'=>14, 'color'=>'#8a919b', 'mt'=>18, 'mb'=>18]];
$pdo->prepare("UPDATE dr_pro SET detail_json=? WHERE id=?")->execute([json_encode($default, JSON_UNESCAPED_UNICODE), $newId]);
```
编辑器打开即整套结构(轮播/商品信息/抢购按钮/信任标记/订单滚动/引导文字), 投手一眼看懂从哪开始改。

配套: 新建向导**不再传主图**(主图上传挪进组件编辑器), 向导第 2 步只剩 商品名称/售价/划线价/库存。

## 4. 投手工作台 UI(卡片视图, 页面为主体)

落地页管理重做(原型先行: 静态 HTML 原型 → 用户确认 → 后端落地):

- **列表**: 卡片网格 `grid-template-columns:repeat(auto-fill,minmax(330px,1fr))`, 每卡 = 主图(150px)/名称/状态徽章/网址/浏览/像素标签(右上角)/售价/库存/操作行
- **操作**: `[🔗 链接] [🧩 详情组件] [⋯]`; ⋯ 菜单 = 页面设置/商品设置/详情组件/像素配置/发布切换/删除
- **新建向导 2 步弹窗**: 步骤条(进度条)+ 第1步页面设置(标题必填/网址选填留空自动生成)+ 第2步商品信息 → 完成创建 → toast → 1.2s 后跳详情编辑器
- **商品设置弹窗**: product_get → vals 数组动态行(售价/划线价/库存三输入, data-i/data-k), addEventListener 绑定更新 pVals; **提交格式 `price_<key>/yprice_<key>/qty_<key>`**——product_edit 用 `preg_match('/^price_(\d+)_(\d+)$/', $k, $m)` 解析, 写成 `<key>_price` 会静默丢价格(保存成功但价格没变)
- **页面设置弹窗**: 标题 + Slug 输入 + 🎲 随机按钮(JS 生成 32 位 hex)+ 提示「修改后旧链接失效」

### 后端 slug 编辑增强(product_edit)
```php
if ($slug === '') {
    do { $slug = bin2hex(random_bytes(16)); $chk = ... WHERE url_slug=? AND id<>?; } while ($dup);
} else {
    $slug = strtolower($slug);
    if (!preg_match('/^[a-z0-9-]{3,64}$/', $slug)) → 400 格式错误
    if (查重排除自己) → 400 已被使用
    if ($slug !== $pro['url_slug'] && isset($sku['myWebUrl'])) $sku['myWebUrl'] = 'https://'.cfg('site_domain').'/'.$slug;  // 同步
}
```

## 5. 像素配置弹窗的控制器命名坑

- 路由 = `{c}_{m}` 拼接(`router()`: `$fn = $ctrl . '_' . $method`)
- 像素配置接口函数名是 **`pixelcfg_save/pixelcfg_status/pixelcfg_delete`**(无下划线)→ URL `c=pixelcfg&m=save/status/delete`
- 按商品查询是 `pixel_cfg_by_pro`(有下划线)→ URL `c=pixel_cfg&m=by_pro`
- 写错下划线 → `{code:0, msg:'方法不存在'}` **静默失败**(不报 500)
- 教训: 新建/改名接口后 `grep "function <前缀>" modules/admin.php` 确认实际函数名, 再写前端 URL

## 6. 编辑器真实数据预览(window.CUR)

编辑器预览不再用占位文字, 注入当前商品数据:

- pro_detail_index 查 `$sku0 = json_decode($pro['sku_json'])` → `$cur = ['title','thumb','price','yprice']` → view 传 `cur` → 模板 `window.CUR = <?php echo json_encode(...)?>`
- JS renderComp:
  - proinfo 预览: `pt = window.CUR.title || '商品标题'`, 价格用 CUR.price/yprice(替换写死的 986/2980)
  - swiper 预览: `var imgs = (p.images && p.images.length) ? p.images : (window.CUR.thumb ? [window.CUR.thumb] : [])`——没配图时自动用主图
- **图片预览所见即所得**: swiper 预览直接 `<img src=... style="width:100%;height:170px;object-fit:cover;...">` 真实图, 不显示「图1: URL 前36字符」占位

## 7. 组件编辑器图片本地上传

属性面板 URL 字段全部支持本地上传:

- 页面放一个隐藏 `<input type="file" id="upFile" accept="image/*" onchange="doUp()">`(全局唯一)
- `upField(k)`: 记录 `_upKey = k` → 触发 file input
- `doUp()`: FormData → `c=product&m=upload`(校验链见主 SKILL 11b)→ 按 `_upKey` 回填:
  - `'images'` → push 进数组(轮播列表)
  - 其他字段(src/image/cover)→ `setProp(k, url)`
  - `'__thumb__'` → 调 `c=product&m=set_thumb`(UPDATE dr_pro.thumb)→ 更新 window.CUR.thumb → refreshThumb() + render()
- renderProps 渲染: text 类型且 k ∈ [src,image,cover] → 输入框旁加 `<button class="up-btn" onclick="upField('k')">📁</button>`; list 类型 → 底部「📁 上传图片加一行」按钮
- **主图上传入口位置**: 组件库「页面组件」分组底部(libThumb 虚线块: 当前主图缩略图 + 📁 上传商品主图), 点击整块触发 upThumb()。**不放顶栏**(用户纠正: 顶栏按钮位置不对, 返回按钮回原位——顶栏保持「← 返回 | 💾 保存详情」原布局)

## 8. 全部组件文字参数化

用户:「所有的组件模拟器里面, 带文字的, 我都要可以自主编辑」「有部分组件, 我不要只能修改商品名字, 我要全部可以修改」。

本次参数化的字段(每个都 PHP 渲染端 + JS 编辑器端同步):

| 组件 | 新增字段 | 默认值 |
|---|---|---|
| reviews | title(标题)/note(尾注)/buytext(订购文案) | 最新評價 / — 以上為近期訂單真實反饋 — / 【訂購了】 |
| form | name_ph/tel_ph(placeholder) | 姓名 / 手機號碼 |
| ticker | action(订购动作)+lines(自定义滚动内容, 每行一条) | 訂購了 / [] |
| product | btntext(按钮文字) | 立即搶購 |

- ticker 渲染逻辑: `lines` 有值 → 原样拼接滚动(每条 + 全角空格); 空 → 自动生成(时间+地区+姓氏+action+【text】)
- product 的 btntext 需要把 props 传入 `detail_render_product($proid, $mt, $mb, $p)`(函数签名加第 4 参)
- **改组件字段 = 五处同步**: PHP detail.php case + JS renderComp case + DEFAULTS + COMP_FIELDS + FIELDS。漏任何一处 = 字段不显示(前端)或保存丢失(白名单/渲染)
- FIELDS 新类型: `t:'list'`(每行一项 textarea, setList 解析成数组)、`t:'trust'`(每行 图标|文字, setTrust 解析成 [[icon,text]])、`t:'faq'`(每行 问题|答案, setFaq 解析成 [{q,a}])

## 9. 编辑器布局三件套(用户连续截图反馈)

### 手机预览固定高度(不要无限拉长)
用户两次纠正: ①「手机样式长度不要一直拉长, 不是可以上下滑动吗」②「太长了, 符合正常手机长度」。
```css
.phone{width:390px; height:844px; max-height:calc(100vh - 150px); display:flex; flex-direction:column; box-sizing:border-box; ...}
.phone-inner{flex:1; min-height:0; display:flex; flex-direction:column; ...}
.phone-screen{flex:1; min-height:0; overflow-y:auto; padding-top:42px}
```
844px = 390×844 标准 9:19.5 手机比例; 窗口矮时 max-height 压缩; 组件多了在屏幕内部滚动, 手机本体长度不变。

### 编辑器贴合侧边栏
admin_layout 的 `.content{padding:24px; max-width:1360px; margin:0 auto}` 会把编辑器居中留白 → 编辑器页覆盖:
```css
.content{padding:0!important; max-width:none!important; margin:0!important}
```
组件库紧贴左侧深蓝侧边栏。

### 移动优先 PC 自适应
用户: 「主做手机端的落地页, 然后 pc 端自适应」。
```css
#pageComps{max-width:100%; margin:0 auto}
@media (min-width:768px){
    body{background:#eef0f3}
    #pageComps{max-width:560px; background:#fff; min-height:100vh; box-shadow:0 0 48px rgba(16,24,40,.08)}
    #checkoutContent{max-width:560px; padding:0 0 40px}
    #desktopFixedButtons,#mobileFloatingButtons{max-width:560px; left:50%; transform:translateX(-50%); right:auto; border-radius:16px 16px 0 0}
    header nav{max-width:560px; margin:0 auto}
}
```
PC 打开 = 手机页面居中(560px 卡片+浅灰背景), 手机全宽不变。编辑一次两端同步。

## 10. 其他实测坑

- **detail_render_product 签名**: 组件需要 props 时函数签名加 `array $p = []` 并从 case 里传 `detail_render_product($proid, $mt, $mb, $p)`, 漏传 = $p 未定义
- **delete 接口名**: 商品删除是 `product_delete`(前端 `m=delete`); 像素删除是 `pixelcfg_delete`(前端 `m=delete`)——统一了但都要 grep 确认
- **测试后清理**: 每次新建测试商品后必须删(delete API), 否则列表残留「111/123123」垃圾卡; 商品 ID 会一直递增(71/72/73/74/75/76…)
- **用户测试页**: 用户自己新建的测试商品(如 75 mengbao-test)不要擅自删, 问用户
- **模板变量确认**: 改模板前 grep view() 传了哪些变量, 优先复用已有变量(如 $sku), 别急着加传参
