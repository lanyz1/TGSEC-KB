# Qavlixor 买家端探针脚本（browser_console 直接粘贴执行）

> 用法：`browser_navigate` 到目标页后，把表达式粘进 `browser_console` 的 expression 参数。
> 注意：Next dev 偶发 DOM 未水合（探针返回空数组）→ 重新 navigate 一次再跑。

## 1. 强饱和色残留扫描（橙/红/蓝等，max-min>45）
```js
(()=>{const sat=[];document.querySelectorAll('.buyer-portal *').forEach(el=>{const s=getComputedStyle(el);for(const prop of ['backgroundColor','borderColor','color']){const m=s[prop].match(/rgb\((\d+), (\d+), (\d+)\)/);if(m){const [r,g,b]=[+m[1],+m[2],+m[3]];if(Math.max(r,g,b)>70&&Math.min(r,g,b)<210&&(Math.max(r,g,b)-Math.min(r,g,b))>45){sat.push({cls:(el.className||'').toString().slice(0,28),c:s[prop]});break}}}});return JSON.stringify(sat.slice(0,10),null,1)})()
```

## 2. 浅粉系残留扫描（近白浅粉——强色探针会放过，必须单独扫）
```js
(()=>{const out=[];document.querySelectorAll('.buyer-portal *').forEach(el=>{const s=getComputedStyle(el);for(const prop of ['backgroundColor','borderColor']){const m=s[prop].match(/rgb\((\d+), (\d+), (\d+)\)/);if(m){const [r,g,b]=[+m[1],+m[2],+m[3]];if(r>245&&g>230&&g<250&&b<245&&(r-b)>8){out.push({cls:(el.className||'').toString().slice(0,28),prop,c:s[prop]});break}}}});return JSON.stringify(out.slice(0,8),null,1)})()
```
已抓到的浅粉类：`#fff0f3`(add-cart)、`#fff8f9`(sku selected)、`#fff7f5`(favorite active/cct-link)、`#fecdd6`(payc 边框)、`#ffe3e9`(stats 分隔线)。

## 3. 字重白名单扫描（抓 850/950/800/900 乱入值）
```js
(()=>{const out=[];document.querySelectorAll('.buyer-portal h1,.buyer-portal h2,.buyer-portal button,.buyer-portal .button,.buyer-portal a').forEach(el=>{const fw=getComputedStyle(el).fontWeight;if(fw&&![400,500,600,700].includes(+fw)&&el.getBoundingClientRect().width>0){out.push({t:(el.textContent||'').trim().slice(0,15),fw,cls:(el.className||el.tagName).toString().slice(0,25)})}});return JSON.stringify(out.slice(0,10),null,1)})()
```
卖家端（.seller-portal）同款，把 `.buyer-portal` 换成 `.seller-portal` 即可——注意选择器列表里 `.buyer-portal button` 那类重置块是**多门户共用**（含 `.seller-portal button`），卖家端按钮一样会被压 8px。

## 4. 元素形态速测（圆角/字重/颜色/背景/边框）
```js
(()=>{const cs=(el,p)=>el?getComputedStyle(el)[p]:'NF';const out={};const grab=(sel,key)=>{const el=document.querySelector(sel);out[key]=el?{r:cs(el,'borderRadius'),fw:cs(el,'fontWeight'),fs:cs(el,'fontSize'),c:cs(el,'color'),bg:cs(el,'backgroundColor'),b:cs(el,'borderColor'),sh:cs(el,'boxShadow').slice(0,40)}:'NF'};grab('.buyer-portal h1','h1');grab('.buyer-portal .catalog-heading h1','title');return JSON.stringify(out,null,1)})()
```

## 5. 层叠规则排查（找哪个选择器最终生效——特异性/文件序决胜）
```js
(()=>{const el=document.querySelector('<选择器>');const out=[];for(const sh of document.styleSheets){try{for(const r of sh.cssRules){if(r.style&&el.matches(r.selectorText)&&r.style.<属性>){out.push({sel:r.selectorText.slice(0,55),val:r.style.<属性>,imp:r.style.getPropertyPriority('<属性>')})}}}catch(e){}}return JSON.stringify(out,null,1)})()
```
实战结论：同 important 同特异性 → 文件靠后赢；`button.类名`(0,2,1) > `.buyer-portal .类名`(0,2,0) > 重置块 `.buyer-portal button`(0,1,1)。

## 6. 布局溢出排查（元素超出容器）
```js
(()=>{const box=document.querySelector('<容器>');const fr=box.getBoundingClientRect();const out=[];box.querySelectorAll('*').forEach(el=>{const r=el.getBoundingClientRect();if(r.right>fr.right+2&&r.width>0){out.push({cls:(el.className||el.tagName).toString().slice(0,35),right:Math.round(r.right),fRight:Math.round(fr.right)})}});return JSON.stringify(out.slice(0,8),null,1)})()
```
注意：details 未展开的隐藏子节点会误报越界（offsetParent 非 null 但不可见）——先看容器 scrollWidth 是否超，再看是否 details.open=false。

## 7. 登录（fetch 保 cookie，比表单点击稳）
买家：
```js
(()=>{return fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'<EMAIL-REDACTED>',password:'<见HANDOFF>'})}).then(r=>r.json().then(d=>({ok:d.ok}))).catch(e=>({error:String(e)}))})()
```
卖家（**必须带 `role:'seller'`，否则商户账号被 403 拒**——返回"该账号是商户账号，请从商户端登录"；成功返回 `entry:'/seller'`）：
```js
(()=>{return fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'<EMAIL-REDACTED>',password:'Demo@2026view',role:'seller'})}).then(r=>r.json().then(d=>({ok:d.ok,entry:d.entry}))).catch(e=>({error:String(e)}))})()
```
在已加载的页面（如 /login 或任意站内页）执行，然后直接 navigate 到目标页。若在 404/空白页执行会报 URL 解析错误——先 navigate 回站内页。

## 8. 金额换算验证（data-currency-lock 是否生效 / 语言切换后金额是否保持 USDT）
```js
(()=>{const bodyText=document.body.innerText;const amounts=document.querySelector('.bod-amounts');const out={};if(amounts)out.amounts=(amounts.textContent||'').trim().replace(/\s+/g,' ');const sf=M=>{const i=bodyText.indexOf(M);return i>=0?bodyText.slice(i,i+40).replace(/\s+/g,' ').trim():'NF'};out.shifukuan=sf('实付款');out.payMethod=sf('支付方式');out.total=sf('商品总价');return JSON.stringify(out,null,1)})()
```
用法：中文态下看"实付款/商品总价"是否仍是 `N USDT`（而非换算成 CNY）——若显示 CNY 说明该区域缺 `data-currency-lock`。语言切换：点导航栏语言按钮 → 菜单里点"简体中文"，等 1s 再跑探针。

