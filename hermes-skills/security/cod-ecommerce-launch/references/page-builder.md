# 组件化落地页编辑器(落地页管理模块)完整模式

马总COD 后台「落地页管理」实战(2026-08): 投手自助建页, 组件库+手机预览+属性面板, 零前端依赖(无 Vue/React/构建)。

## 数据模型

```sql
CREATE TABLE dr_page (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE,            -- 自动生成 p_<md5(uniqid) 12位>, 唯一
  title TEXT, config TEXT,     -- config = JSON {bg, components:[{type,props}]}
  status INTEGER DEFAULT 1, hits INTEGER DEFAULT 0,
  inputtime INTEGER, updatetime INTEGER
);
CREATE TABLE dr_page_lead (    -- 表单组件提交的线索
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pid INTEGER, name TEXT, tel TEXT, inputtime INTEGER
);
```

slug 路由接入(util.php route_by_slug): pro 查完查 page, 命中 → require modules/page.php + page_show($page)。

## 组件 schema(17 个, 4 组)

| 组 | 组件 | props |
|---|---|---|
| 基础 | title | text, size, color, align, bold, mt, mb |
| 基础 | text | text, size, color, align, bold, mt, mb |
| 基础 | divider | color, mt, mb |
| 基础 | space | h |
| 媒体 | image | src, radius, mt, mb |
| 媒体 | fullimg | src, link, mt, mb |
| 媒体 | video | src, cover, mt, mb |
| 媒体 | card | image, title, text, bg, mt, mb |
| 转化 | button | text, bg, color, link, full(通栏), radius, size, mt, mb |
| 转化 | product | proid(绑定 dr_pro 真实商品) |
| 转化 | countdown | text, end(datetime-local), bg, color, mt, mb |
| 转化 | form | text(按钮文案), bg, pid(关联落地页), mt, mb |
| 转化 | reviews | title, rating(0-5 小数支持), count(2-20), product(商品名留空用默认), mt, mb |
| 内容 | notice | text, bg, color, mt, mb |
| 内容 | label | text, bg, color, size, radius, mt, mb |
| 内容 | faq | items:[{q,a}], mt, mb |
| 内容 | footer | text |

### reviews(最新評價)组件实现要点

- **信任营销组件**: 头部(红底刷新 SVG 图标 + 标题 + 星级评分)→ N 条评价 → 底部「— 以上為近期訂單真實反饋 —」
- **星级支持小数**(4.6): 5 颗中第 4 颗做 partial 填充(外层 overflow:hidden + width:百分比 内层 ★)
- **随机条目**(JS/PHP 双端各自实现, 每次 render/访问重新随机): 姓氏池 20 个 + 地区池 20 个(台湾县市)+ 脱敏手机 `09XX***XXXX` + 时间「X分鐘前/X小時前」递推(2+rand(55)+i*(8+rand(40)))
- props: rating(评分)/ count(条目数, clamp 2-20)/ product(商品名文案, 默认【猛豹久硬挺】：壯陽補腎神藥)
- 数据全内置, 不落库——纯展示组件(假订单滚动列表同思路, 但这里是独立组件可插任意位置)

## 双端渲染(必须一致)

- **编辑器 JS** `renderComp(c)`: switch(type) 返回 HTML 字符串, props 直接拼 style
- **前台 PHP** `page_render_component(array $c)`: 同样 switch, 输出到 page_show.php 模板
- 动态组件: 倒计时 `data-end` unix 秒 + JS setInterval tick 显示 HH:MM:SS; 公告 CSS translateX 循环; 表单 fetch POST `/index.php?s=page&c=api&m=lead` → 落 dr_page_lead → json_out(1)
- 商品卡: PHP 端查 dr_pro(status=1) 渲染图/标题/NT$价格(取 value 第一个档)/划线价/立即搶購链接; 不存在或下架显示红色提示卡

## 编辑器三栏布局(单模板, ~24KB)

```
┌─────────┬──────────────────┬─────────────┐
│ 组件库   │ 手机预览          │ 属性面板     │
│ 分组h4   │ .phone 440px      │ 页面设置tab  │
│ .lib-item│  钛金属+灵动岛    │ 选中组件tab  │
│ 点击添加  │ .comp 拖拽排序    │ 动态表单     │
│ 拖拽     │ 选中高亮+浮层工具  │ ↑↓删除      │
└─────────┴──────────────────┴─────────────┘
顶部常驻工具条: [标题输入] /slug  [👁预览] [💾保存] [←返回列表]  ← sticky top:56px z-index:30
```

- **大坑(用户反馈): 保存/返回按钮放右侧「页面设置」tab 里, 选中组件后被属性面板盖住 = 找不到保存按钮**。修复: 顶部 sticky 工具条常驻(保存/预览/返回任何状态可见), 页面设置 tab 保留但按钮冗余无害; 顶栏标题输入与页面设置标题输入双向同步(DOMContentLoaded 绑定 input 事件互写)
- **iPhone 17 Pro Max 手机预览**(按真实规格, 2025-09 机型): 宽 440px(6.9" 1320pt@3x)、外壳圆角 66px + 内屏 56px、钛金属渐变边框(#d6d8db→#8e9196)、**灵动岛**(绝对定位悬浮胶囊 128×38px 居中 + 摄像头黑点 radial-gradient)、侧边音量±/电源键装饰(pseudo-element 胶囊)。**坑: 灵动岛绝对定位悬浮在内容上 → 预览区顶部必须垫 66px spacer**(render() 里 innerHTML 前置 `<div style="height:66px">`), 否则组件被岛遮挡且点击区域错位

- 组件库点击添加: LIB 里找 type 的 defaults JSON.parse(JSON.stringify) 深拷贝 → push → render
- 拖拽排序: comp draggable, dragstart 记 dragFrom, drop 时 splice 移动
- 属性面板: COMP_SCHEMA[type] 字段数组 → FIELDS[k] 表单描述(text/number/color/check/select/datetime/pro/faq)→ 动态生成表单, onchange setProp 后 render() 实时预览; faq 类型专用行编辑器(增删问答)
- 页面设置 tab: 背景色 color picker + 标题 + 只读落地页 URL + 保存/预览/返回
- 保存: POST {id, title, config: JSON.stringify({bg, components})} → page_save 服务端校验

## 服务端安全校验(page_save)

```php
$cfg = json_decode($config, true);           // 必须数组且含 components
$allowed = ['title','text',...];             // 16 类型白名单
foreach ($cfg['components'] as $c) if (!in_array($c['type'], $allowed)) 拒绝;
```

## 控制器方法(admin.php)

page_index(列表+搜索+统计)/ page_add(建页+slug)/ page_save / page_status(上下架)/ page_delete / page_leads(线索 JSON)/ page_editor(id → 编辑器模板, 附商品列表供 proid 下拉)

## API 测试陷阱(重要)

控制器函数结尾 `exit`(json_out 风格), **同进程 PHP 测试脚本连续调用会被第一个 exit 截断**——本地验证要么每步独立进程, 要么直接部署后用 curl 服务器实测(本会话实测: curl 全链路 7 步一次通过)。

## 实测结果(服务器, 2026-08)

- 列表页 200 / 27KB; 编辑器 200 / 45.6KB(组件库/手机预览/页面设置全渲染)
- 新建 → 保存 6 组件(标题/倒计时/商品卡/按钮/FAQ/表单) → 前台 slug 200 / 4.9KB 全组件渲染
- 表单提交 code:1 + 线索落库可见; 非法组件类型 {"code":0} 拦截
- 测试数据清理: DELETE dr_page / dr_page_lead
