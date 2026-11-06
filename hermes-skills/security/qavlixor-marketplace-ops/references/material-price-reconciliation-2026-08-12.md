# 素材价格对账与错版重复商品清理(2026-08-12 实录)

## 背景
批量铺货(素材(1) 48 个拓竹商品 → LivvyHome 店)后,用户报"有些商品价格特别高"。
排查发现两类问题:① 补变体时价格靠拍脑袋估算(全错);② 铺货产生同店同标题重复商品(错版+正确版并存)。
用户两次纠正:"注意货币单位"、"不要估算,要有事实有依据"。

## 权威价格源 = 桌面素材 txt(不是猜、不是 Amazon 现价)
`C:\Users\Administrator\Desktop\素材(1)\<品类>\<商品>\商品信息.txt` 每份含:
- `默认价格(USDT)*: <数值>` — **已是 GBP 原价按素材标注汇率(1.3486)换算的 USDT 价**,不要再用别的汇率重算
- `SKU明细: 规格名|编码|USDT价格|库存; ...` — 每个 SKU 的权威价格(无运费)
- `首件运费: <数值>` — **运费规则因品类而异,必须逐份读,不能假设统一值**

## 运费规则(2026-08-12 核实,已入库)
| 品类 | 首件运费 | 平台售价公式 |
|---|---|---|
| 打印机(11 素材:a1/a1-mini/a2l/h2c/h2d/h2s/p1s/p2s/x2d/Combo 套装) | 60 | 素材USDT价 + 60 |
| 耗材(37 素材:pla*/petg*/abs/asa/tpu*/pva/pc*/support* 等) | 8 | 素材USDT价 + 8 |

平台售价 = 素材 USDT 价 + 首件运费(运费折进售价,用户拍板规则),SKU 明细价格同步。
**验证锚点**:H2D AMS Combo Standard = 1954.12+60 = 2014.12 ✅、ABS = 24.26+8 = 32.26 ✅。

## 对账方法论(有据可依,无估算)
1. **提取素材权威价**:遍历素材目录读 商品信息.txt,正则取 `默认价格(USDT)*` + `SKU明细`(名称|编码|价格|库存)+ `首件运费`,存 JSON(`_material_prices.json`)。
2. **拉生产全量**:paramiko 脚本(sftp 传 .mjs → node 执行)取全部 3d-printer 类目商品 + variants(price/stockQuantity),拉回本地 JSON。
3. **标题关键词匹配素材**:每个生产商品标题按关键词表(如 "a1 combo + led"→A1-Combo-LED-Kit)映射到素材;耗材按名字匹配(pla-basic→pla-basic-filament 等)。
4. **对比**:期望价 = 素材 SKU 价列表 + 运费(按品类),排序后与生产实际价排序比对,`len 相同 && 每对 |Δ|<0.01` 为 ✅。
5. **⚠️ 对账脚本必须按品类用正确运费**:第一版对账脚本对耗材也 +60 → 全部误报 ❌(实际是素材+8=正确)。运费规则错了全表误报,先验证锚点商品再批量判。
6. **人工确认误报**:标题含 TPU/3D/Resin 的跳绳/手机壳/餐具等是材质/造型词,不是 3D 打印,保持原类目。

## 重复商品判定(同店同标题才是真重复)
- 跨店铺同标题 = 素材分发正常(167 组,不动)。
- **同店铺同标题 = 真重复**:用标题规范化键(小写去非字母数字,截前 40 字符)分组,`arr.length>1` 即组。
- 组内"正确版"判定:变体数与素材 SKU 数一致 **且** 价格 = 素材+运费;错版 = 单变体/价格不符/`-SKU-MAIN` 后缀(手工补的)。
- **正确版可能已存在**(如 A2L 正确版 1116433434 有 3 变体 490.2/638.55/705.98)——先全店查再决定删还是补,别默认要重建。

## 已删除的错版/重复商品(10 个,全有正确版保留,2026-08-12)
| 删除(错版) | 保留(正确版) |
|---|---|
| PD2608121117033615 H2D 1049.99 | PD2608121114342618 H2D 6变体 2014.12~2958.14 |
| PD2608121114457013 H2S 899.99 | PD2608121117144475 H2S 3变体 1339.82~1946.69 |
| PD2608121114226450 H2C 799.99 | PD2608121116527658 H2C 4变体 2620.99~3565.01 |
| PD2608121114093635 A2L 689.99 | PD2608121116433434 A2L 3变体 490.2~705.98 |
| PD2608121113423796 A1 479.99 | PD2608121116154439 A1 2变体 490.2/341.86 |
| PD2608121113586290 A1 mini 284.99 | PD2608121116345824 A1 mini 2变体 409.29/260.94 |
| PD2608121113112969 A1 Combo+LED 529.99 | PD2608121115450869 A1 Combo+LED 525.27 |
| PD2608121113224612 A1 mini+LED 838.96 | PD2608121115557240 A1 mini+LED 287.91 |
| PD2608121113323453 P1S Combo(手工SKU-MAIN) | PD2608121116066890 P1S Combo(B0CHDS1DMC 素材SKU) |
| PD2608111232591037 P1S 旧版 485.24/674.47 | PD2608121117242738 P1S 3变体 503.69~759.92 |

删除脚本:级联 `productVariant/productImage/productOperationMetric/buyerFavorite`(deleteMany)再 `product.delete`。
注意:BuyerFavorite(不是 ProductFavorite)、ProductVariant 无 barcode 字段、sku 全局 @unique。
删后 bump CatalogVersion(4 实例缓存失效)。最终 LivvyHome 3D 商品 44 个、重复组 0、无变体 0。

## Nova Print Studio(直营店)31 个商品 = Amazon 采集价,不是素材体系
fill-bambu.mjs 从 Amazon 采集(SKU=Amazon ASIN 1200005xxx,如 X2D 3300.99/P1S 927.99),
价格是 Amazon 真实价,**不属于素材(48 个)+60/8 规则,不能按素材改**。
对账时先分清两套数据源,别把 Amazon 价当错误。

## Prisma 直查脚本坑(本会话反复踩)
- 服务器脚本 `.mjs`(ESM):禁 TS 类型注解(`let x: string|null` SyntaxError);`require` 报 ReferenceError → `await import("@prisma/client")`;try 块内不能 `return`(SyntaxError)。
- `include` 与 `select` 互斥(PrismaClientValidationError);ProductVariant 无 name 字段(用 optionValues)、无 barcode。
- 正则 `+` 必须转义(`\+ ams`,否则 "Nothing to repeat")。
- 生产查询一律 paramiko + sftp 传 .mjs + `unset PYTHONPATH` 临时 venv。
