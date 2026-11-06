# 演示数据联动 + 脚本注入 + 从基准重建(单文件原型实战)

## 1. 工作台日期切换器模式(seg 按钮 + DASH_DATA)

给单文件原型加"按日期切换 KPI"的可交互演示(用户:懂我意思不?——要能切换查看多天数据):

```html
<!-- 页头:日期 sub 加 id,旁边插 seg(样式复用 .seg/.seg button.on) -->
<div class="sub num" id="dashDate">Aug 1, 2026 · Saturday</div>
<div class="seg" id="daySeg" style="margin-right:10px">
  <button data-day="731">7/31</button><button data-day="801" class="on">8/1</button><button data-day="802">8/2</button>
</div>
<!-- KPI 值标签加 id:kSales/kOrders/kCust(childNodes[0] 是文本节点) -->
```

```js
var DASH_DATA = {
  '731': {date:'Jul 31, 2026 · Friday', sales:'13,725.60', orders:'344', cust:'344', vs:'—', cls:'d num'},
  '801': {date:'Aug 1, 2026 · Saturday', sales:'18,792.90', orders:'471', cust:'471', vs:'▲ 36.9% vs yesterday', cls:'d up num'},
  '802': {date:'Aug 2, 2026 · Sunday', sales:'10,733.10', orders:'269', cust:'247', vs:'▼ 42.9% vs yesterday', cls:'d down num'}
};
function setDay(d){
  var D = DASH_DATA[d]; if(!D) return;
  document.getElementById('dashDate').textContent = D.date;
  var s=document.getElementById('kSales'), o=document.getElementById('kOrders'), c=document.getElementById('kCust');
  s.childNodes[0].nodeValue = D.sales + ' ';   // 保留 <small>USDT</small>
  o.childNodes[0].nodeValue = D.orders + ' ';
  c.childNodes[0].nodeValue = D.cust;
  [s,o,c].forEach(function(el){ var dd=el.parentNode.querySelector('.d'); dd.className=D.cls; dd.textContent=D.vs; });
  document.querySelectorAll('#daySeg button').forEach(function(b){ b.classList.toggle('on', b.dataset.day===d); });
}
// 绑定:document.readyState==='loading' ? DOMContentLoaded : 直接 bind
```

要点:
- KPI 值标签带 `<small>USDT</small>` 时,`childNodes[0]` 是文本节点,改它保留单位;无 small 的直接 textContent
- 切换按钮绑定用 `e.target.closest('button')` + `dataset.day`,别用内联 onclick(多按钮循环绑定)
- 涨幅箭头类 `d up num`(绿▲)/`d down num`(红▼)/`d num`(持平或—),由 cls 字段控制

## 2. 演示数据联动规则(同源,勿自造)

用户改一个数时,整条数据链要联动(否则 KPI/图表/待办/资金自相矛盾被用户一眼看穿):
- **销售额 = 客单价 × 订单数**(客单价固定 39.9 时,只给单数/客户数即可算出销售额)
- **涨幅 = (今 − 昨) ÷ 昨**(昨日常给,如"昨日订单 471")
- **待结算 = 当日订单销售额全额**(无平台佣金,订单全额入待结算;余额是历史已结算,不随当日变)
- **图表锚点/末三位数据与 KPI 同源**(7/31=344、8/1=471、8/2=269 → sales30 末三位对应,锚点 `new Date(2026,7,2)`,末端标注=最后一位值;y 轴网格随 max×1.15 自动)
- **待办未发货/已发货合计 = 多日订单总和**(随机分配未发货 85-170 区间,已发货 = 总和 − 未发货)
- 用户纠正单位时立刻记住:客户数是**人数**(无单位),销售额才带 USDT——别把客单价塞进"今日客户"卡

## 3. 注入新 `<script>` 块的正确姿势

翻车实录(本会话 DASH_DATA undefined 两次):
1. 裸 JS 字符串插在第一个 `</script>` 后 → 浏览器当 HTML 文本,不执行。UI 渲染正常但 `window.变量` undefined
2. `find('</script>')` 定位的第一个结束标签 + 再包裹 `<script>` → 插入点其实在主 script 内部,截断主 script + 残留裸文本
正确做法:**完整 `<script>...</script>` 块插到 `</body>` 前**,验证 `window.你的变量 !== undefined` 并实际调用函数。

## 4. 从基准重建(交付文件被删/移走时)

桌面交付文件可能被用户删/移走(本会话:zip/规格/CSS 全消失,只剩基准 HTML + 2 个新文件)。**基准 HTML 是唯一事实源**,全部文件可重新生成:
- 基准 CSS:`<style>` 块整体导出(53KB,原样)
- 登录页样板:切 `view-login` section + 全量 CSS + 激活脚本组装独立 HTML
- 部署目录:Dockerfile + nginx.conf(hash 路由 try_files + gzip)重写
- 规格/指令/清单文档:重写(内容在会话上下文/记忆中,不在文件里)
教训:先 `ls` 确认现状再动手,别假设文件还在;重建后重新打包交付。
