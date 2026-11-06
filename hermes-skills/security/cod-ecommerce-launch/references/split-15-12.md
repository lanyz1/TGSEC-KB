## 12. 组件化落地页编辑器(投手自助建页, 零前端依赖)

投手要能自己新建/改落地页(参照 SAAS 落地页工具的组件库+手机预览模式), 纯原生 PHP+JS 实现的模式:

1. **数据模型**: `dr_page(id, slug UNIQUE, title, config JSON, status, hits, inputtime, updatetime)` + `dr_page_lead(pid, name, tel)`(表单线索); slug 自动生成 `p_<md5 12位>`, 接入 `route_by_slug`(pro 查完查 page)
2. **配置 JSON 双端渲染**: `{bg, components:[{type, props}]}` —— 前端编辑器 JS `renderComp()` 实时预览, 前台 `modules/page.php` `page_render_component()` PHP 渲染, 两套实现同一组件 schema(必须保持一致)
3. **编辑器三栏布局**(单模板内联 JS/CSS): 左=组件库(分组: 基础/媒体/转化/内容, 点击或拖拽添加)→ 中=手机预览(390px 模拟, HTML5 drag 排序 + 选中高亮 + 上移/下移/删除浮层)→ 右=属性面板(按 FIELDS schema 动态生成表单, onchange 实时 setProp 重渲染)
4. **组件集(16 个够用)**: title/text/divider/space/image/fullimg/video/card/button/product/countdown/notice/label/faq/footer/form; 商品卡组件从 dr_pro 读真实商品(图/价/购买链), 倒计时前台 JS 每秒 tick, 公告 CSS transform 滚动
5. **安全**: page_save 服务端校验 JSON + 组件 type 白名单(非法直接拒); 文本 htmlspecialchars; 链接仅 http(s)
6. **API 测试陷阱**: 控制器函数结尾 `exit`(json_out 风格), 同进程连续调用测试脚本会被截断——逐进程测或直接 curl 服务器实测
7. 完整 schema/编辑器 JS 结构/实测结果: 见 `references/page-builder.md`

