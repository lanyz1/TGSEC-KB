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

