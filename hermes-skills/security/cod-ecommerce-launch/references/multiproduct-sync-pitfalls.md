# 多商品同步铁律 + 多 SKU 体系 + fail2ban 误封(生产实测补充)

本文件是 `multiproduct-workbench.md` 的补充, 记录多商品化后「后台改/前台不同步」类问题的完整根因族、POST 解析顺序陷阱、多 SKU(规格名+缩略图)三端实现, 以及 fail2ban 误封后台的运维坑。全部来自马总COD/xeelee.top 生产实测。

## 1. 「后台修改和前台不同步」根因族(全部实测)⭐

用户报告「后台修改和前台不同步什么情况」时, 按下面顺序排查(都是**硬编码/漏同步**问题, 不是缓存):

### 1a. 改标题 → sku_json 的 group/name 不同步(结算/订单数据用旧标题)

- **症状**: 后台商品设置改了标题, 页面/标签显示了新标题, 但前台结算数据、订单里的商品名还是旧值。
- **根因**: `product_edit` 只 `UPDATE dr_pro SET title=?`, **sku_json 里的 `group['0']` 和 `name['0'][i]` 还是旧标题**——前台结算(SkuComponent)读的是 sku.group/name。
- **修复**: title 变更时同步:
  ```php
  if ($title !== $pro['title']) {
      foreach ($sku['group'] as $gk => $gv) $sku['group'][$gk] = $title;
      foreach ($sku['name'] as $nk => $nv)
          if (is_array($nv)) foreach ($nv as $n2 => $v2) $sku['name'][$nk][$n2] = $title;
      $changed[] = '标题';
  }
  ```
- **注意 $changed 初始化顺序**: `$changed[] = '标题'` 必须发生在 `$changed = []` 之后, 否则被覆盖(ops_log 丢字段, 无功能影响但日志不对)。
- **诊断**: `php -r '...echo "db=".$x["title"]." sku.group=".$s["group"][0];'` 对比 db title 与 sku.group——不一致即此坑。

### 1b. 下单/结算价格硬编码(改价后前台显示新价但提交旧价)

- **症状**: 后台改价后页面价格变了, 但**结算页显示价/下单提交价/广告平台上报价还是旧价**(986)。
- **位置**: pro_show.php 三处写死 `986`: ① AddToCart 像素 value(两处, 106/120 行)② **`priceshow:'986'`(Vue data, 结算页显示与下单价)**。ViewContent 像素之前也硬编码过(见 multiproduct-workbench §2)。
- **修复**: 全部动态取当前商品价(模板里 `$sku` 已由 pro.php view 传入, 无需新变量):
  ```php
  value: '<?php echo htmlspecialchars($sku['value']['0_0']['price'] ?? ''); ?>'
  priceshow:'<?php echo htmlspecialchars($sku['value']['0_0']['price'] ?? ''); ?>',
  ```
- **验证铁律**: 改价 → 前台 grep 三处同步(`priceshow:'<新价>'` + 像素 value + NT$ 显示), 再改回还原。**grep `'986'` 残留必须 = 0**。
- 下单链路(order.php)本身从 sku 实时取价(无需改), 前端 totalPrice = selectedSku.price × quantity 也实时——**只有写死的字面量会脱同步**。

### 1c. 全套硬编码检查清单(多商品化后必做)

```bash
grep -n "id=61\|id='61'" .htaccess                 # 伪静态硬编码转发(劫持所有新商品链接!)
grep -n "【猛豹久硬挺】\|<title>" templates/pro_show.php   # 标题/像素商品名硬编码
grep -n "'986'\|986'" templates/pro_show.php       # 价格硬编码(priceshow/像素 value)
grep -n "= \$\$title\|group.*title" modules/admin.php      # sku 同步逻辑
```
任何「单商品时代」写死的商品名/ID/价格在**多商品化改造时全部参数化**, 一处漏 = 一个"不同步" bug。

## 2. POST 多档参数解析顺序陷阱(规格图丢失)⭐

- **症状**: 新建商品带多档规格图(image_0_0/0_1/0_2), 保存后 sku.image 数组全是空字符串。
- **根因**: product_add 的多档解析是 `elseif` 链, image 分支带 `isset($values[$key])` 前置检查——**前端 URLSearchParams 按追加顺序发送, `image_0_0` 在 `price_0_0` 之前 append, 到达时 `$values['0_0']` 还没创建 → isset 为 false → 图片被静默跳过**。
- **修复**: 不依赖顺序——image 分支独立创建条目:
  ```php
  } elseif (preg_match('/^image_(\d+)_(\d+)$/', $k, $m)) {
      $key = $m[1] . '_' . $m[2];
      if (!isset($values[$key])) {
          $values[$key] = ['image' => trim($v), 'price' => '', 'quantity' => '1000', 'sn' => '', 'yprice' => ''];
      } else {
          $values[$key]['image'] = trim($v);
      }
  }
  ```
- **通用教训**: 多字段解析循环里, 任何字段都可能先于"创建条目"的字段到达——**每条分支都做成可独立创建条目**(price/name/image 都要能初始化 $values[$key]), 别依赖 POST 顺序。

## 3. 多 SKU 完整体系(规格名 + 规格缩略图 + 价格档)⭐

用户要求「价格档还需要加上 sku 规格, 不同的 sku 需要不同的 sku 名字」「不同的 sku 我要上传不同的商品缩略图, 前端下单的时候可以看到那种」。

### 数据模型(对齐原版 sku 结构)

```
sku_json:
  group:  { '0': '規格' }                  ← 组名(前台「套餐選擇」下的组标题)
  name:   { '0': ['1盒裝', '3盒裝', '5盒裝'] }  ← 每档规格名(前台选项文字)
  image:  { '0': ['/uploads/a.png', ...] } ← 每档规格缩略图(前台选项图片)
  value:  { '0_0': {image, price, quantity, sn, yprice}, '0_1': {...}, ... }
```
前台结算 SkuComponent 已原生支持规格图: 选项模板 `v-if="images[gid][optionIndex]"` 显示 80×80 缩略图——**只要把 sku.image['0'][i] 填上 URL, 前台自动显示**, 无需改模板。

### 三端参数(后台表单 ↔ 控制器)

| 字段 | 前端 append | 控制器正则 |
|---|---|---|
| 规格名 | `name_0_0` / `name_0_1` | `/^name_(\d+)_(\d+)$/` → `$sku['name'][$m[1]][$m[2]]` |
| 规格图 | `image_0_0` | `/^image_(\d+)_(\d+)$/` → value[$key]['image'] + image[$m[1]][$m[2]] |
| 售价/划线/库存 | `price_0_0` 等 | 见 multiproduct-workbench §4 |

- **product_add**(新建): 解析 name_/image_/price_/yprice_/qty_ 全部 0_i 格式; 无 name 参数时兜底 `'規格'.($i+1)`; `ksort($vnames, SORT_NUMERIC)` 保证 name/image 数组顺序与 value 键一致
- **product_edit**(编辑): 同正则回写; product_get 每档返回 `{key, name, image, price, yprice, qty}`(vals 数组加 name/image 字段)
- **前端行渲染**(新建向导 renderWVals + 商品设置弹窗 renderVals 同款): `[42px 缩略图📁] [规格名] [售价] [划线价] [库存] [🗑]`——缩略图 div 点击触发隐藏 file input → 专用上传函数(wUpImg/pUpImg)上传后 `wVals[i].image = url; renderWVals()`
- **提交循环**: `wVals.forEach((v,i) => fd.append('name_0_'+i, ...) + image_0_i + price_0_i + yprice_0_i + qty_0_i)`——**image 必须 append 在 price 之前也会正常(见 §2 修复)**

### 前端结算效果

「規格」组下每个选项 = 规格缩略图 + 规格名, 点选切换价格/库存; 多档商品建档时**规格名/图/价/库存一步配齐**。

## 4. fail2ban http-get-dos 误封后台(运维坑)⭐

- **症状**: 某台机器访问站点「无法访问此网站」(Connection refused / icmp unreachable), 其他机器正常; 后台操作频繁的机器最容易中招。
- **根因**: `http-get-dos` jail 的 filter(`failregex = ^<HOST> -.*"(GET|POST|HEAD).*`)匹配**所有 HTTP 请求**——默认 `maxretry=60, findtime=300`(5 分钟 60 次请求=1 次/4 秒)就把正常后台操作/刷新当 DoS 封了(REJECT 80/443, bantime 600s)。
- **诊断**: `fail2ban-client status http-get-dos` → Banned IP list 里看到用户机器 IP; `iptables -L f2b-http-get-dos -n` 确认 REJECT 条目。
- **修复**:
  ```bash
  fail2ban-client set http-get-dos unbanip <IP>        # 立即解封
  # jail.local: [http-get-dos] maxretry 60→300, bantime 600→300(正常操作 1 次/秒内不会触发)
  fail2ban-client reload
  ```
- **预防**: 后台是高频操作场景, http-get-dos 阈值必须远高于正常使用量(建议 maxretry≥300); 固定办公 IP 可加 `ignoreip`(注意用户 IP 可能是动态的)。后台有脚本轮询/自动刷新时更容易触发。

## 5. 主图 = 组件(mainimg, 用户最终决策)⭐

用户连续两次纠正主图入口: ①「主图怎么放在了右上角...返回那个按钮还是放回原位置」(顶栏不放)②「上传主图, 不是这个意思, 我的意思是把主图也当成一个组件」(侧边栏 libThumb 块也被否决)。

**最终形态**: 组件库「页面组件」组第一个 = 「主图」组件(与轮播图/商品信息并列), 完全组件化:

- 属性面板: `src`(text + 📁 上传)/ `radius` / `mt` / `mb`; 预览 `p.src || window.CUR.thumb`, 无图显示占位
- PHP detail.php: `case 'mainimg': $mi = $p['src'] ?? ($ctxPro['thumb'] ?? '');` 渲染 `<img>`(空 src 不输出)
- **保存同步**: pro_detail_save 里遍历 comps, 找到 mainimg 且有 src → `UPDATE dr_pro SET thumb=?`——列表卡片/商品卡/默认轮播(swiper 无图时用 thumb)全部一致
- 白名单 $allowed 加 'mainimg'; DEFAULTS/COMP_FIELDS/FIELDS 五处同步(见 workbench §8 五处同步铁律)

**教训**: 用户对"特殊位置的上传入口"(顶栏按钮/侧边栏块)反感, 明确要「所有东西都是组件」的统一模型——后台任何资源入口先问自己: 能不能做成组件?
