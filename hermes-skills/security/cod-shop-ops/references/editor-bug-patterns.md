# 编辑器/后台 Bug 实战案例(2026-09 马总COD zengda 系统)

## 案例 1:模块串行(组件索引污染)
**现象**:调组件上下位置错乱——点 A 组件的 ↑,B 组件被换走;评价/轮播图组件渲染后整页组件点击全乱。
**根因**:`renderComp(c, i)` 中 `for (var i = 0; i < cnt; i++)` 覆盖函数参数 `i`;循环结束后包裹层
`onclick="selectComp(' + i + ')"` / `moveComp(' + i + ',-1)` 的 i 变成循环终值(如 5)→ 选中/移动/删除全部错位。
**修复**:7 处 `for (var i` → `for (let i`。
**排查命令**:`grep -n "for (var i" templates/admin_pro_detail.php`
**预防**:渲染/模板函数内循环一律 let 或独立变量名;若用 var,循环后保存原索引副本。

## 案例 2:输入框重建(中文只能打一个字)
**现象**:编辑器属性面板输入文字,敲一个字符光标跳末尾/输入法断掉,中文只能输入首字。
**根因**:`oninput → setProp → render()` 全量重建(预览 innerHTML + 面板 innerHTML)→ 输入框 DOM 销毁重建。
**修复**:render 拆分 `renderScreen()`(只重建手机预览)+ `renderProps()`(重建面板);
oninput 只调 renderScreen;onchange/失焦调 syncProps() 重建面板同步格式化值。
**注意**:textarea(faq/trust/list)同样处理;doUp 上传后也只 renderScreen。

## 案例 3:多 SKU 保存丢失(新增档消失/删除档复活)
**现象**:商品设置弹窗加一档保存 → 重开又没了;删一档保存 → 重开还在。
**根因**:`product_edit` 用 `isset($sku['value'][$key])` 过滤 → 新档(旧 sku 无此键)被跳过;删除的档无清理逻辑。
**修复**:
- price_/yprice_/qty_/name_/image_ 分支:键不存在时**自动创建条目**(image 分支独立创建,不依赖 price 先到)
- 提交档键集(以 price_ 为准)→ 移除 sku['value'] 中未提交键(删除生效)
- value 键**重新编号 0_0/0_1/0_2**,同时 name['0']/image['0'] array_values 重排(索引对齐,防规格错位)
- 前端 addValRow 新档 key = 当前最大序号+1(防删档后撞号)
**验证**:增档→保存→get 回显 3 档;删档→保存→get 回显 2 档且键连续。

## 案例 4:POST 参数顺序导致字段丢失
**现象**:创建商品时 image_0_0 传了但 sku.image 数组为空。
**根因**:POST 发送顺序 name_0_0, image_0_0, price_0_0, ...;image 分支 `isset($values[key])` 检查时
条目尚未被 price_ 创建(price 在后)。
**修复**:image 分支不依赖其他字段——不存在即独立创建完整条目。

## 案例 5:价格硬编码 986(后台改价前端不同步)
**现象**:商品设置改价 998,页面显示 NT$998 但结算页/下单/像素还是 986。
**根因**:pro_show.php 三处硬编码 `'986'`:FB 加购像素 value ×2 + Vue `priceshow:'986'`。
**修复**:全部改为 `<?php echo htmlspecialchars($sku['value']['0_0']['price'] ?? ''); ?>`。
**教训**:COD 保真模板大量硬编码业务值(标题/价格/像素 content_name),迭代前先 `grep -n "'986'\|【猛豹\|value: '"` 清场。

## 案例 6:运费 NaN
**现象**:结算页「运费: NT$NaN 合计: NT$NaN」。
**根因**:运费由地区联动 updateShippingFee 设置,未选地区时 skuData.yunfei = undefined → Number(undefined)=NaN。
**修复**:显示 `Number(skuData.yunfei || 0)`;mounted initSkuData 里 `this.skuData.yunfei = Number(...) || 0`;
data-updated 提交链路同步兜底。
**扩展**:商品级固定运费存 sku['yunfei'],新建向导/商品设置可配;updateShippingFee 无地区费时兜底 fixedFee。

## 案例 7:fail2ban 误封「无法访问此网站」
**现象**:其他机器访问后台 443 被拒(REJECT icmp-port-unreachable)。
**根因**:http-get-dos filter 匹配所有 GET/POST,`maxretry=60 findtime=300` → 后台操作 >60 次/5分钟被 ban 600s。
**修复**:jail.local http-get-dos `maxretry = 300 / bantime = 300`;`fail2ban-client set http-get-dos unbanip <IP>`;
reload 后 iptables 链只剩 RETURN。常用办公 IP 加 ignoreip。

## 案例 8:.htaccess 硬编码路由劫持
**现象**:新建落地页链接(/32位hex)打开显示旧商品内容;编辑器数据 vs 前台完全对不上。
**根因**:单商品时代的 `RewriteRule ^([a-f0-9]{32})$ index.php?s=pro&c=show&m=index&id=61 [L]`。
**修复**:改为 `RewriteRule ^([a-f0-9]{32})$ index.php [L]` → route_by_slug 按 slug 查库。
**教训**:多商品化/多租户化必查 .htaccess/nginx rewrite 是否还有硬编码 id。

## 案例 9:标题不同步 sku_json
**现象**:商品设置改标题,前台 <title>/部分数据仍显示旧名。
**根因**:product_edit 只 UPDATE dr_pro.title;sku['group']/sku['name'][0][0] 还是旧标题(下单/结算数据用它)。
**修复**:title 变更时同步 `$sku['group'] = ['0' => $title]`(或'規格')、`$sku['name']['0']`;thumb 变更同步 sku['thumb']/sku['image']。

## 案例 10:评论组件自动滚动(JS 驱动)
**现象**:CSS `@keyframes rvUp + animation:rvUp 20s linear infinite` 用户浏览器实测不动。
**根因**:CSS keyframes 在部分浏览器/环境不生效;无独立验证手段。
**修复**:JS 驱动——内联 IIFE:读 `t.scrollHeight/2` 得 half,`setInterval 30ms y-=1`,`Math.abs(y)>=half 归零`,双份内容无缝;悬停暂停(mouseenter clearInterval / mouseleave 重启)。id 随机防多实例冲突。
**编辑器端**:renderScreen() 末尾调 initRV()(data-rv 标记防重复绑定)。
**验证**(无 CDP 时):
```
chrome --headless=new --disable-gpu --no-sandbox --proxy-server=socks5://127.0.0.1:10808 \
  --proxy-bypass-list=<-loopback> --virtual-time-budget=6000 --dump-dom URL | grep translateY
```
transform 为负值且在变 = 滚动运行中。

## 案例 11:主图联动(图片组件上传改了主图)
**现象**:在图片/轮播组件上传图,保存后商品主图/列表卡片变成新图。
**根因**:pro_detail_save 里有「mainimg 组件 src 自动同步 dr_pro.thumb」逻辑——页面只要含主图组件,保存就写 thumb。
**修复**:删除自动同步;thumb 唯一入口 = 商品设置弹窗。上传提示改「只更新当前组件」。
**用户规则(硬性)**:「在哪里上传的图片,就显示在哪里」——组件图片完全隔离,永不自动联动商品字段。

## 部署/验证惯例
- 本地 PHP 语法检查:`D:/tools/php83/php.exe -l file.php`
- 服务器 curl:`curl -sk 'https://127.0.0.1/<slug>' -H 'Host: xeelee.top' -o /tmp/x.html` + grep 关键标记
- 数据库直查核对(商品名/价格/thumb/sku 结构)
- 测试数据清理:product_delete(id);列表剩正式商品即可
- 本机 python3 无 paramiko 时用 `python`(venv 有 paramiko 5.0.0)
- 编辑器 get 返回 comps 非空即编辑器数据正常;前台 pageComps 渲染对比
