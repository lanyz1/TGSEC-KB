## 11b. 后台图片本地上传模式(商品管理/任意表单)

- **uploads 目录**: `<docroot>/uploads/`(chown apache:apache 755), 上传接口 POST `?s=admin&c=product&m=upload`(admin_require + `$_FILES['file']`)
- **校验链**: ① error 码 → ② 大小 ≤3MB → ③ **`getimagesize()` 真实图片校验**(伪造后缀直接拒) → ④ 扩展名白名单 `[IMAGETYPE_JPEG=>jpg, PNG, WEBP, GIF]` → ⑤ **随机文件名** `pro_<date>_<md5 10位>.<ext>`(不可预测) → move_uploaded_file + chmod 0644 → 返回 `{code:1, url:'/uploads/xxx'}`
- **安全铁律: uploads/.htaccess 禁 PHP 执行**(上传点即使被塞 webshell 也无法运行):
  `<FilesMatch "\.(php|php5|phtml|phar|pl|py|cgi)$"> Require all denied </FilesMatch>`(实测 403)
- **前端**: 隐藏 `<input type=file accept="image/*">` + 「📁 选择图片上传」按钮触发 → FormData fetch 上传 → 回填隐藏 URL 输入框 + 预览 div(内联 img); 弹窗里预览占位 56×56 灰底「无图」
- **编辑弹窗数据源**: 专用 `product_get` 接口返回全量(标题/slug/主图/全部价格档数组 vals:[{key, price, yprice, qty}]), 弹窗按 vals 动态生成每档三输入(售价/划线价/库存, `data-k="price_<key>"`), 提交时 collect 全部 `[data-k]` 输入 → product_edit 按 `price_(\d+)_(\d+)` 正则循环回写 sku_json
- **主图同步三处**: dr_pro.thumb + sku_json.thumb + sku.image['0']['0'] + value['0_0'].image(只改一处会导致落地页/列表/详情图不一致)

