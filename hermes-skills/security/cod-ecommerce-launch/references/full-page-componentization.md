# 商品页整页组件化 + 投手工作台(马总COD 迭代实战)

本轮把商品页从"保真模板+详情组件"升级为**整页组件化**(23 组件 5 组), 并把落地页管理重做为投手工作台。全部服务器实测通过。

## 1. 整页组件化架构

- **23 组件 5 组**(编辑器组件库顺序):
  - 页面组件: swiper(轮播图, images 每行 URL / height)/ proinfo(商品信息, proid+show_title/show_price/show_yprice 开关)/ buybtn(抢购按钮, text/bg渐变/color/size/radius/full)/ trust(信任标记, rows 每行 图标|文字)/ ticker(订单滚动, text/action/lines)
  - 基础: title/text/image/fullimg/video/button
  - 营销: countdown/reviews/product/marquee
  - 内容: card/label/faq/form/footer
  - 装饰: divider/space/notice
- **默认头部**: `detail_default_header($pro)` = [swiper(thumb), proinfo, buybtn, trust, ticker]; `detail_has_header()` 检查 swiper/proinfo/buybtn 任一存在即不补; pro.php 渲染与 pro_detail_get **都**要 merge 默认头部(旧商品零改动自动获得新头部)
- **商品页模板**: mainContent 整段 → `<div id="pageComps"><?php echo $detailHtml; ?></div>`; 结算表单/底部悬浮按钮/Swiper JS/像素/指纹全部保留
- **模板变量名坑**: view() 传 `'content' => $detailHtml` 但模板用 `$detailHtml` → pageComps 渲染为空(空白页, 页面 200 无错误)。**view 键名与模板变量必须一致**, 或两个都传
- **Swiper 通用初始化**: `.swiper-page` class; `document.querySelectorAll('.swiper-page').forEach(el => new Swiper(el, {loop:true, speed:500, pagination:{el:el.querySelector('.swiper-pagination'), clickable:true}, autoplay:{delay:5000, disableOnInteraction:false}}))` + try/catch
- **showCheckout 全局化**: ready 内 function 声明是局部作用域, 组件按钮 onclick="showCheckout()" 调不到 → `window.showCheckout = showCheckout`; buybtn 渲染 onclick 双保险 `try{showCheckout()}catch(e){document.getElementById('cnmallOrder').click()}`

## 2. 移动优先 PC 自适应

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
手机<768px 全宽不变; 编辑一次两端同步。

## 3. 编辑器 UI 三连修(用户截图反馈驱动)

1. **手机预览固定高度**(不再无限拉长, 用户"符合正常手机长度"):
   ```css
   .phone{width:390px;...;height:844px;max-height:calc(100vh - 150px);display:flex;flex-direction:column;box-sizing:border-box}
   .phone-inner{...;flex:1;min-height:0;display:flex;flex-direction:column}
   .phone-screen{flex:1;min-height:0;overflow-y:auto;padding-top:42px}
   ```
   844px = 390×844 标准 9:19.5; 窗口矮时 max-height 压缩; 组件多时**屏幕内滚动**。
2. **贴合侧边栏**(用户"与左侧 cod 靠齐不要居中"): admin_layout `.content{padding:24px;max-width:1360px;margin:0 auto}` 导致编辑器居中 → 编辑器页覆盖:
   `.content{padding:0!important;max-width:none!important;margin:0!important}`
3. **主图上传位置**(用户"主图放左侧页面组件底下, 返回放回原位置"): 顶栏按钮被否 → 组件库「页面组件」分组底部虚线框:
   ```html
   <div id="libThumb" style="margin:10px 0 4px;border:1.5px dashed #c9ced6;border-radius:10px;padding:8px;text-align:center;cursor:pointer" onclick="upThumb()">
       <img id="libThumbImg" style="width:100%;max-height:90px;object-fit:cover;border-radius:8px;display:none">
       <div style="font-size:11.5px;color:var(--ozon);font-weight:600;padding:4px 0">📁 上传商品主图</div>
   </div>
   ```
   上传 → `product_set_thumb` 接口(新加, UPDATE dr_pro.thumb)→ `window.CUR.thumb = url` + refreshThumb() + render()。

## 4. 图片本地上传(属性面板)

- FIELDS 的 text 类型对 `src/image/cover` 键自动加 `📁` 按钮(upField(k) → 隐藏 `<input type=file id=upFile onchange=doUp()>` → `product&m=upload` → setProp)
- list 类型(images 轮播)加「📁 上传图片加一行」: 上传后 `c.props.images.push(url)`
- doUp() 统一处理: `_upKey` 记录目标字段; `__thumb__` 走 set_thumb 分支
- 上传后 render() 立即在手机预览显示真实图片(所见即所得); swiper 预览直接 `<img>`(170px cover), 不再文字占位

## 5. 所有带文字的组件可编辑(用户铁律)

硬编码文案全部参数化, **PHP detail.php 与 JS renderComp 双端同步**, DEFAULTS/COMP_FIELDS/FIELDS 三处补:
- reviews: title(标题)/note(尾注)/buytext(订购文案【訂購了】)/rating/count/product
- form: name_ph/tel_ph(placeholder)/text/bg/pid
- ticker: text(商品名)/action(订购动作)/lines(自定义滚动内容每行一条, 留空自动生成随机)
- product(商品卡): proid/btntext(按钮文字, detail_render_product 签名加 `array $p = []`)

## 6. 新建即默认页面(不空白)

product_add 创建后:
```php
require_once __DIR__ . '/../lib/detail.php';
$dpro = ['id' => $newId, 'title' => $title, 'thumb' => $thumb, 'sku_json' => json_encode($sku, JSON_UNESCAPED_UNICODE)];
$default = detail_default_header($dpro);
$default[] = ['type' => 'text', 'props' => ['text' => '👆 这是你的落地页! 点上方组件可在右侧编辑; 从左侧组件库添加更多模块(图片/倒计时/评价/FAQ/表单…)', 'align'=>'left', 'size'=>14, 'color'=>'#8a919b', 'bold'=>0, 'mt'=>18, 'mb'=>18]];
$pdo->prepare("UPDATE dr_pro SET detail_json=? WHERE id=?")->execute([json_encode($default, JSON_UNESCAPED_UNICODE), $newId]);
```

## 7. ⭐ .htaccess 硬编码 slug→id 劫持

症状: 新建落地页链接(32 位 hex)打开显示旧商品内容, 编辑器与前台对不上。
根因: 单商品时代 `RewriteRule ^([a-f0-9]{32})$ index.php?s=pro&c=show&m=index&id=61 [L]` — 所有 32 位 hex 硬编码转发到 id=61。
修复: `RewriteRule ^([a-f0-9]{32})$ index.php [L]`(去参数, route_by_slug 按 slug 查)。
诊断: 前台 h1 ≠ 该商品标题 → grep .htaccess/vhost RewriteRule 硬编码 id; `index.php?s=pro&c=show&m=index&id=<id>` 直连对比确认模块正常。
教训: **"单商品假设"硬编码(固定 id/slug)在支持多商品后就是隐藏劫持; 新建商品功能上线后 grep 全站硬编码残留 + 实测两个不同商品链接**。

## 8. 投手工作台 UI 模式

- 原型先行: 写可交互 HTML(open_preview)让用户确认再后端化
- 卡片列表(主图/像素角标/状态/网址/meta + [🔗 链接][🧩 详情组件][⋯])
- 2 步向导: 页面设置(标题/网址)→ 商品信息(名称/价格/库存, 无主图)→ product_add → 跳 pro_detail
- 商品设置弹窗: product_get vals 多档; 提交键格式 `price_0_0/yprice_0_0/qty_0_0`(**匹配后端正则 `^price_(\d+)_(\d+)$`**, `0_0_price` 静默不生效)
- 像素配置弹窗: 新接口 `pixel_cfg&m=by_pro` 按商品查; **控制器名是 `pixelcfg` 无下划线**(pixelcfg_save/status/delete), 路由 {c}_{m} 拼接, 差一个下划线 = "方法不存在" {code:0} 静默失败
- 部署环境(Windows): `python3` 可能指向 WindowsApps(无 paramiko), `python` 指向 hermes venv(有 paramiko 5.0.0) — 部署脚本用 `python`; PHP 语法检查 `D:/tools/php83/php.exe -l`
- 大段 HTML 替换(patch 匹配失败时): Python 按行定位 start/end 索引切片替换
- 测试数据清理铁律: 每轮 API 测试后清商品/像素/线索, 只剩正式 #61; 验证 `grep -c` 关键文案

## 9. 本轮新增后端接口

- `product_set_thumb(id, thumb)` — 更新 dr_pro.thumb(组件编辑器主图上传)
- `pixel_cfg_by_pro(proid)` — 按商品查 dr_pixel_cfg(落地页内像素弹窗)
