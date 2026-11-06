## 12g. 新建落地页 = 添加商品(单页 COD 产品模式)⭐

- **用户提出**: 商品就是落地页, 那「新建落地页」就是完整添加商品——后台商品概念完全退居幕后, 落地页管理是唯一入口
- **按钮文案(方案A 后)**: 「+ 新建卖货页」(商品即落地页, 含下单); 曾叫「+ 新建落地页」, 砍掉自定义页后统一为卖货页
- **新增弹窗完整表单**: 落地页标题(商品名)/ Slug / 主图本地上传 / 售价 / 划线价 / **库存** / ☑ 创建后进入详情组件编辑器
- **product_add 支持 qty**(写进 sku_json value['0_0'].quantity, 不再硬编码 1000)
- **创建后跳转**: doAdd 成功 → checkbox 勾选 → `location.href = '/index.php?s=admin&c=pro_detail&m=index&id=' + j.id`(直接搭详情)→ 否则 alert + reload
- 投手完整流程: 新建落地页(标题/主图/价格/库存)→ 自动进详情组件编辑器 → 保存 → 复制链接投放; 以后改: ⋯ → 编辑
- 底层: 一个落地页 = 一个 dr_pro 商品(标题/价格/库存/详情全落库), 前台商品页即时可访问
- **旧表补列铁律**: 服务器旧库缺新列时(`dr_fb_event` 缺 `capi_status` 等)→ db.php 初始化 `try { $pdo->exec("ALTER TABLE ... ADD COLUMN ..."); } catch (Exception $e) {}` 容错补列(无 IF NOT EXISTS 语法, 已存在会抛错正好吞掉); 部署后访问一次页面触发建列, 再用 PRAGMA table_info 验证

