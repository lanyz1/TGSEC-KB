## 9. 后台模块扩展(占位菜单 → 真功能)

后台侧边栏占位菜单(商品/区域/IP黑名单/操作日志/系统设置/关于)转真模块四件套:

1. `templates/admin_layout.php`: 菜单项 url 从 `'#'` 改为 `/index.php?s=admin&c=<mod>&m=index`(去掉 data-placeholder="1" 即不再弹"开发中" toast) + crumbMap 加 `'<mod>' => '中文名'`
2. `modules/admin.php`: 加 `function <mod>_index()`(admin_require + 查询 + view) + 编辑/删除 POST 方法返回 `{"code":1}`
3. `templates/admin_<mod>.php`: `require admin_layout.php; admin_head('标题', '<mod>')` + `.stats` 统计卡(5 卡网格) + 筛选卡 + `.table-wrap` 表格 + 分页
4. 编辑/删除前端 fetch POST, alert + location.reload()

模式要点: 统计卡/搜索/分页全部复用 admin_layout 的 CSS 类(.stat/.c-blue/.btn/.badge/.tbl), 零新样式; 分页 = `LIMIT n OFFSET m` + COUNT(*) 双查询; 父级名称同表 `WHERE region_id IN (...)` 预加载 map。完整实现示例(区域管理 15483 条浏览/筛选/搜索/编辑/删除): `references/admin-module-pattern.md`

**区域树维护(地区=树, 下单联动即时生效)**: 每行操作 `[+ 下级] [编辑] [删除]`; 添加下级 = `MAX(region_id)+1` 组内新 ID + `INSERT OR IGNORE`(防冲突)+ 同组 parent_id 存在性校验; 编辑弹窗含名称/编码/邮编/**父级(region_id, 0=顶级)**; **防环铁律**: 父级不能是自己(`$pid === $row['region_id']` 拒)+ 不能移到自己的后代(沿 parent_id 链向上走, 遇到自己即拒); `parent_id=0` 是顶级标记——**0 必须跳过存在性检查**(否则误报"父级地区不存在")。保存后下单页地区联动**即时可见**(同一 linkage_ld 接口)。

