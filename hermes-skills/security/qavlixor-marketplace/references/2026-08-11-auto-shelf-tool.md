# 2026-08-11 卖家本地自动上品工具（CLI + Web UI）

用户需求：卖家在自己电脑上按 Excel 模板批量上架商品。交付两版工具（均在 `D:\跨境商城\会话产物\` + 桌面副本），实测跑通。

## CLI 版 `qavlixor_auto_shelf.py`

- 依赖：`pip install openpyxl requests`
- 用法：`python qavlixor_auto_shelf.py --excel 模板.xlsx --email 卖家邮箱 --password 密码 [--status 草稿|已上架] [--limit N] [--no-images]`
- 登录：`POST /api/auth/login` body `{role:"seller", email, password}` → requests.Session 自动带 cookie（gm_session）
- 图片：模板"主图URL/详情图URL"支持 https 链接 **或本地路径**（本地图先 `POST /api/uploads` multipart `file` → 返回 url 拼 base）；多图 `;` 分隔
- 提交：`POST /api/seller/products`，字段对齐发品表单：title/brand/category/status/price/inventory/skuItems/detail/shippingNote/productParams/shipBy；images 数组 `[{url}]` 前 12 张
- 限速 0.4s/条防风控；单条失败不中断
- 翻译：新商品走异步翻译管线，首次翻译有延迟属正常

## Web UI 版（用户要求"好看的前端 UI"）

- `qavlixor_shelf_ui.py`（自带 `http.server` 服务，端口 8765，线程跑任务 + `/api/state` 轮询进度）+ `shelf_ui.html`（暗色科技风：`#0a0e1a` 底 + 蓝紫渐变 + 毛玻璃卡片 + 进度条/统计/滚动日志）+ `启动上品工具.bat`（双击启动）
- 前端文件选择用 `f.path`（拖拽/选择拿绝对路径传后端）；后端 `os.path.isfile` 校验
- bat 必须 GBK 编码 + CRLF（用户偏好）；`chcp 65001` 避免中文乱码
- 视觉验证：browser_vision 评估过（深色科技感协调专业）

## 关键点

- **模板 16 列**：商品标题*/品牌/分类/默认价格(USDT)*/默认库存*/SKU明细/主图URL/详情图URL/卖点文字/产品参数/运费方式/首件运费/续件运费/包邮门槛/发货时限/保存状态；示例行靠"标题非空"过滤跳过
- 上架被保证金拦时工具会原样显示平台 message（补缴后重跑即可）
- Excel 模板文件：`Qavlixor卖家端批量上传商品模板.xlsx`（会话产物，openpyxl 生成，无宏）

## 后续可扩展（用户提过）

断点续跑（失败行记录 CSV）、并发提速、多账号、上品前预览表格
