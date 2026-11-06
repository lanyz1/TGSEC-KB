# 组件编辑器最终态纠正 + 评论自动滚动(2026-08 迭代)

> 本节**覆盖** `editor-js-bugs-and-multiproduct.md` 与 `multiproduct-workbench.md` 中
> 「mainimg 组件保存时同步 `dr_pro.thumb`」的旧描述——该行为已被用户否决(见下)。

## 1. ⭐ 图片上传不联动主图(用户最终裁决: 在哪里上传, 就显示在哪里)

**用户报**: 「别的图片模块添加图片, 主图会关联更换」——在任何图片组件上传图, 保存后商品主图/列表卡片被换成新图。

**根因**: pro_detail_save 曾实现「遍历 comps, 有 mainimg 组件且 src 非空 → `UPDATE dr_pro SET thumb=src`」。页面里只要有 mainimg 组件, 任意组件上传+保存都会触发 thumb 覆盖。

**最终态(铁律)**:
- `pro_detail_save` **不做任何 thumb 同步**——组件图片只属于组件本身
- 商品主图(thumb)唯一修改入口 = 「落地页管理 → ⋯ → 商品设置」弹窗
- mainimg 组件 src 空时默认显示当前 thumb(`window.CUR.thumb`), 但传图只改组件
- 清理死代码: doUp 的 `__thumb__` 分支、upThumb()、refreshThumb() 全删
- 上传成功 toast: 「✓ 图片已上传, 只更新当前组件」

## 2. 评论组件自动滚动(无缝循环)

**用户报**: 「评论组件要做成那种自己滚动的」。

实现(前台 PHP 渲染 + 编辑器 JS 预览双端同步):

```html
<div class="rv-scroll" style="height:XXXpx;overflow:hidden;position:relative">
  <div class="rv-track" style="animation:rvUp 20s linear infinite">条目...条目...</div>
</div>
```

```css
@keyframes rvUp{0%{transform:translateY(0)}100%{transform:translateY(-50%)}}
.rv-track{will-change:transform}
```

- **条目 HTML 输出两份(×2)**, 动画位移 -50% = 恰好滚过一份 → 首尾无缝循环, 永不断档
- 滚动窗口高度按 count 自适应: `max(70, min(222, ceil(count*0.55)*74))` px(显示 1~3 条)
- keyframes 必须在 **pro_show.php(前台)和 admin_pro_detail.php(编辑器预览)各定义一份**, 否则对应端不滚动
- 条目样式: `padding:9px 16px 6px;border-bottom:1px solid #f5f6f8`; 标题行/评分/尾注在滚动区外固定
- 20s 一圈; 内容仍随机生成(地区/姓氏/脱敏手机/动态时间)

## 3. 其他最终态要点(2026-08)

- 组件默认间距(防粘连): proinfo mb:10, trust mt/mb:10, buybtn mt/mb:10——已有商品的 detail_json 需批量补
- 手机预览固定 844px(9:19.5), 内部滚动
- PC 端 560px 居中自适应(见 multiproduct-workbench.md §9)
- 新建商品自动写入默认页面配置(detail_default_header + 引导文字), 编辑器不空白
- 编辑器内主图上传入口已移除(用户纠正: 顶栏放主图按钮位置不对 → 后改为组件, 见 §1)
