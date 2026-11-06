## 12j. 后台列表 UI 迭代坑(操作列/弹层/手机预览)⭐

用户连续截图反馈 UI 细节时的三类高频坑(全部实测修复):

- **操作列横向放不下**: 3 个按钮(取消发布/复制链接/⋯)总宽 >220px 溢出表格右缘。修复: 精简为 2 个紧凑按钮 `[🔗 链接] [⋯]`(height 24px/padding 0 8px/字号 11.5px, 总宽 ~90px), **取消发布/编辑/详情组件/像素设置/删除全部收进 ⋯ 下拉菜单**(取消发布按状态显示 ✕取消发布/✓发布, 红色 danger 类)
- **⭐ 弹层被表格容器裁剪(「被条挡住了」)**: `.table-wrap{overflow:hidden}`(圆角+阴影裁剪)会把 absolute 定位的 ⋯ 下拉菜单切掉——菜单根本看不见。**修复模式: 弹出层用 `position:fixed` + 打开时 `getBoundingClientRect()` 计算视口坐标**(右对齐按钮 `left = min(r.right - mw, innerWidth - mw - 8)`, 底部空间不足 `top + 180 > innerHeight` 时向上弹 `top = r.top - 180 - 4`), z-index 100。**任何圆角卡片容器内的弹出层都必须 fixed 定位, 别用 absolute**
- **手机预览顶部白条**: 原结构 `.phone-bar`(34px 白底)+ `.phone-notch` 居中 → 灵动岛上方一条白色状态栏条, 不真实。修复(最终形态): **去掉 phone-bar, notch 改 `position:absolute; top:8px; left:50%; transform:translateX(-50%)` 悬浮在 `.phone-inner` 顶部, 内容区 `.phone-screen` 加 `padding-top:42px` 避让**——灵动岛悬浮在内容上, 像真实 iPhone(与 page_editor 的 66px spacer 方案同理, 白条必须消除)
- **控制器方法名不统一**: 删除接口叫 `product_delete` 但前端 POST `m=del` → 「方法不存在」{code:0}(不报 500 但操作静默失败)。改接口名/新建接口后 grep 前后端方法名一致; 用后台 API 测试删除/状态类操作前先 `grep "function product_" modules/admin.php` 确认
- **按钮类 UI 验证**: 上传后 `grep -c` 关键类名/文案(op-link/more-btn/取消发布)确认渲染; 弹层交互必须真浏览器点(CDP 或人工), 静态 grep 看不到裁剪问题

