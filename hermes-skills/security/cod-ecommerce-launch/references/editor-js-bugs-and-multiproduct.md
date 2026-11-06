# 组件编辑器 JS 两大杀手坑(串行 / 输入重建)⭐

用户报「调组件上下位置有 bug」「模块串行」「每个组件的编辑器都存在 bug」时,先查这两个模式(全部实测):

## ① `for (var i)` 污染组件索引参数(串行 bug)

`renderComp(c, i)` 里任何 `for (var i = 0; i < N; i++)` 都会**覆盖函数参数 i**(var 函数作用域)→ 该组件渲染后,包裹层的
`onclick="selectComp('+i+')"` / `moveComp('+i+',±1)` / 选中态 `state.sel === i` 全部指向循环结束值 →

- 点选选不中
- 上下移把**别的**组件换走(串行)
- 删除删错组件

reviews/swiper/faq/card/trust/product 等所有含循环的组件都中招。

**修复**: 全部改 `for (let i ...)`(块级作用域)。
排查命令: `grep -n "for (var i" templates/admin_pro_detail.php`; 部署后服务器 `grep -c "for (var i"` 应为 0。
同类坑: map 回调里用 var 声明的中间变量也会污染同函数其他分支。

## ② oninput 全量重渲染(输入框每敲一字重建)

`oninput → setProp → render() → 预览+属性面板全部 innerHTML 重建 → 输入框销毁重建` →

- 光标乱跳
- 中文输入法只能打第一个字
- 连续输入错乱

所有带文字输入的组件(标题/文本/按钮/FAQ/评价/表单/信任标记…)全部受影响。

**修复模式**:

```js
function render(){ renderScreen(); renderProps(); }
/* 只刷新预览区(输入属性时不重建面板, 保住输入框焦点/输入法) */
function renderScreen(){
    var scr = document.getElementById('screen');
    if (!state.comps.length) { scr.innerHTML = '<div class="empty-detail">🈳 详情区为空<br>点击左侧组件开始搭建</div>'; return; }
    scr.innerHTML = state.comps.map(renderComp).join('');
}
```

- oninput 只更新 props + `renderScreen()`(面板不重建 → 焦点/输入法保留)
- 输入框加 `onchange="syncProps()"` 失焦时 `renderProps()` 重建面板同步显示
- text/number/textarea(faq/trust/list)全部按此处理

# 伪静态/模板硬编码劫持(新建页面显示旧商品内容)⭐

用户报「新建的商品也显示这个」「网址/标题/价格对不上」时,按此排查链(全部实测命中):

## .htaccess 硬编码商品 id 劫持所有新链接

单商品时代写的死规则:

```
RewriteRule ^([a-f0-9]{32})$ index.php?s=pro&c=show&m=index&id=61 [L]
```

→ **任何 32 位 hex slug 的新落地页全部渲染商品 61**!(用户看到「新建的商品也显示【猛豹久硬挺】」)

**修复**: 多商品后改为

```
RewriteRule ^([a-f0-9]{32})$ index.php [L]
```

交给 `route_by_slug` 按 slug 精确查 dr_pro(再查 dr_page, 404 兜底)。

诊断: 前台 curl 新 slug 看渲染标题是否是另一个商品; `grep RewriteRule .htaccess` 找硬编码 id。
同时注意: 后台 get/前台渲染正常但伪静态 URL 内容错 = rewrite 层问题, 别在应用层排查。

## 保真模板硬编码值必须全部参数化

pro_show.php 里写死值导致两类不同步:

| 位置 | 硬编码 | 后果 |
|---|---|---|
| `<title>【猛豹久硬挺】：壯陽補腎神藥</title>` | 商品名 | 所有商品浏览器标签显示旧商品名 |
| 像素 `content_name/content_ids:'【猛豹久硬挺】'` | 商品名 | 所有商品像素上报旧商品名 |
| 像素 `value:'986'`(ViewContent/AddToCart) | 价格 | 改价后像素上报旧价 |
| 结算 `priceshow:'986'` | 价格 | 后台改价后下单页/提交还是旧价 |
| FB 加购 `value:'986'`(两处) | 价格 | 同上 |

排查: `grep -n "'986'\|猛豹久硬挺" templates/pro_show.php`
修复: 全部改为 `$pro['title']` / `$sku['value']['0_0']['price']` 动态注入(模板已有 $pro/$sku)。

验证: 后台改价 → 前台 grep `priceshow:'新价'` + `value: '新价'` 全同步 = 完成。

## 改标题不同步 sku group/name

product_edit 只 UPDATE dr_pro.title, sku_json 里 `group`/`name` 还是旧标题 → 前台结算/套餐选择显示旧名(「后台修改和前台不同步」)。

修复: 改标题时同步遍历 `$sku['group']` + `$sku['name']` 全量替换(注意 `$changed = []` 初始化位置要在同步逻辑之后, 否则日志丢失)。

# fail2ban http-get-dos 误封后台 + 多 SKU 全链路 ⭐

## fail2ban 误封(「别的机器无法访问网站」)

症状: 其他机器访问 https://站点 显示「无法访问此网站」, 服务器本地 curl 正常。

根因: `http-get-dos` jail 的 filter 匹配**所有 GET/POST**(failregex `^<HOST> -.*"(GET|POST|HEAD).*`), maxretry 60/findtime 300 → **后台正常操作 5 分钟 60 次请求就被封 80/443**(iptables REJECT icmp-port-unreachable)。

诊断:

```bash
fail2ban-client status http-get-dos      # Banned IP list
iptables -L f2b-http-get-dos -n          # REJECT 源
cat /etc/fail2ban/jail.local             # 阈值
```

修复:

```bash
fail2ban-client set http-get-dos unbanip <ip>
# jail.local: maxretry 60 -> 300(≈1 req/s 正常操作绝不触发), bantime 600 -> 300
fail2ban-client reload
```

常见办公 IP 可加 ignoreip。

## 多 SKU 档位增删改(商品设置弹窗)

用户报「新建 sku 保存后再次打开又没有了」:

product_edit 原来 `isset($sku['value'][$key])` 才更新 → **新增档保存后丢失**。

铁律:

1. 价格/划线价/库存/规格名/缩略图各字段**不存在即自动创建条目**(默认 `['image'=>'','price'=>'','quantity'=>'1000','sn'=>'','yprice'=>'']`)
2. 提交包含价格档时**同步删除未提交的旧档**(删除生效)
3. **将 value 键重编号 0_0/0_1/0_2**(保证与 `name['0']`/`image['0']` 索引一致——否则删中间档后前台规格错位 → selectedSku undefined → NaN)
4. 前端 addValRow 新档 key 取 `max(现有序号)+1` 防撞号

```php
// 档位同步: 提交包含价格档时, 移除未提交的旧档 + 重新编号
$submittedKeys = [];
foreach ($_POST as $k => $v) {
    if (preg_match('/^price_(\d+)_(\d+)$/', $k, $m)) $submittedKeys[$m[1] . '_' . $m[2]] = 1;
}
if ($submittedKeys) {
    $newValue = []; $vi = 0;
    foreach ($sku['value'] as $key => $val) {
        if (!isset($submittedKeys[$key])) continue;
        $newValue['0_' . $vi] = $val; $vi++;
    }
    $sku['value'] = $newValue;
    if (isset($sku['name']['0'])) $sku['name']['0'] = array_values($sku['name']['0']);
    if (isset($sku['image']['0'])) $sku['image']['0'] = array_values($sku['image']['0']);
}
```

## POST 参数顺序坑

后端按 `isset($values[$key])` 收集多档时, **image_0_0 先于 price_0_0 到达会因条目未创建被跳过**(表单字段顺序: name/image/price/yprice/qty)。

修复: image 分支也独立创建条目(不依赖 price 先到)。

## SKU 规格名 + 规格缩略图

- `sku.name['0']` = 规格名数组、`sku.image['0']` = 缩略图数组、value 键 `0_i` 三者索引对齐
- product_get 的 vals 每档返回 name/image
- 向导/商品设置每档行 = [📁 缩略图(42px 上传预览)] [规格名] [售价] [划线价] [库存] [🗑]
- **前台结算规格选择模板本来就支持 `images[gid][optionIndex]` 显示缩略图**——只需把 sku.image 填上(v-if 已有)
- 规格名默认: 空 → `規格N`

## 商品级固定运费

- sku_json 加 `'yunfei' => $freight`(新建向导 + 商品设置弹窗输入, product_add/edit 均收 freight)
- 前台 `updateShippingFee` 兜底 `const fixedFee = Number(this.skuData.yunfei) || 0`(地区运费配置优先, 无则固定运费)
- **未选地区时 yunfei undefined → `Number(undefined)` = NaN → 运费/合计显示 NT$NaN**(用户实测报「运费: NT$NaN」)
- 修复: 显示处 `Number(skuData.yunfei || 0)` + `initSkuData` 里 `this.skuData.yunfei = Number(this.skuData.yunfei) || 0`

## 主图 = 组件(mainimg)

用户否决侧边栏上传块(「主图也当成一个组件」)→ 组件库页面组件组加 `mainimg`(src/radius/mt/mb):

- 默认显示当前商品 thumb(`window.CUR.thumb`)
- **保存时检测 mainimg 组件的 src 同步 `UPDATE dr_pro SET thumb`**(列表卡片/商品卡一致)
- 编辑器属性面板 src 字段已有 📁 上传按钮

## 编辑器显示真实商品数据(所见即所得)

- pro_detail_index 把当前商品 `window.CUR = {title, thumb, price, yprice}` 注入模板
- proinfo 预览显示真实标题/价格(不再「商品标题/NT$986」占位)
- swiper 无图时用主图兜底
- 图片类组件预览直接渲染 `<img>`(onerror 隐藏), 上传后 render() 立即显示原图
- 轮播图预览: 真实图片 170px cover 排列(不是「图1: URL前36字符」占位)

## 新建自动默认页面配置(不空白)

- product_add 创建时写入 `detail_default_header($dpro)` + 引导文字组件 → 编辑器打开即有整套结构(轮播/商品信息/抢购/信任/订单滚动)
- **默认组件间距避免视觉粘连**(用户报「信任标记和商品信息联在一起」): proinfo mb:10, trust mt/mb:10, buybtn mt/mb:10
- 已有商品的 detail_json 需批量补间距脚本(遍历 props, 0 → 10)

## 整页组件化 + PC 自适应

- pro_show 内容区整体替换为组件渲染(`<div id="pageComps"><?php echo $detailHtml; ?></div>`)
- 页面级组件: swiper/proinfo/buybtn/trust/ticker/mainimg(头部, 缺则 `detail_default_header` 自动补)
- 渲染时 detail_json 空 → 从 content HTML 迁移组件(`detail_html_to_components`)
- PC 端自适应(用户「主做手机端, PC 自适应」):

```css
#pageComps{max-width:100%;margin:0 auto}
@media (min-width: 768px){
    body{background:#eef0f3}
    #pageComps{max-width:560px;background:#fff;min-height:100vh;box-shadow:0 0 48px rgba(16,24,40,.08)}
    #checkoutContent{max-width:560px;padding:0 0 40px}
    #desktopFixedButtons,#mobileFloatingButtons{max-width:560px;left:50%;transform:translateX(-50%);right:auto;border-radius:16px 16px 0 0}
    header nav{max-width:560px;margin:0 auto}
}
```

- 抢购按钮组件 onclick `try{showCheckout()}catch(e){document.getElementById('cnmallOrder').click()}` 双保险(showCheckout 是 ready 内局部函数, 需提升全局或在 onclick 兜底)
- view() 传参变量名与模板必须一致(曾传 `content` 模板用 `$detailHtml` → 页面空白, pageComps 为空)
