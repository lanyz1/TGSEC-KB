// buyer-color-probe.js — 买家端颜色残留扫描探针(饱和色 + 浅粉系)
// 用法: 整段单行复制进 browser_console 的 expression 参数。
// 警告: browser_console 的 expression 必须单行紧凑,多行/带注释会报
//   SyntaxError: Unexpected end of input(本会话实测踩坑)。
// 逻辑: 遍历 .buyer-portal 下所有元素,取 color/backgroundColor/borderColor/boxShadow,
//   ① 饱和色: 过滤近黑(max<70)/近白(min>210)/灰(max-min<45)/合法徽章色(绿#34C759 蓝#0071E3
//      橙#FF9500 红#FF3B30/#D70015),只报真饱和残留;
//   ② 浅粉/浅橙(2026-08-05 C3 教训): 近白浅粉底如 #fff0f3/#fff8f9/#fff7f5 的 max-min 只有
//      8-18,会被饱和探针的 min>210 或 max-min<45 过滤放过,肉眼却是明显粉底 ——
//      必须加第二条判定: r>245 && 230<g<250 && b<245 && r-b>8。
// 每次改完跑两遍判定,输出 {saturated, pinkish}。
// 截图不可靠、tab 短命,探针最稳(交接文档 §八)。

(()=>{const ok=[[52,199,89],[0,113,227],[255,149,0],[255,59,48],[215,0,21]];const eq=(a,b)=>a.length===b.length&&a.every((v,i)=>Math.abs(v-b[i])<3);const sat=[];const pink=[];document.querySelectorAll('.buyer-portal *').forEach(el=>{const s=getComputedStyle(el);['color','backgroundColor','borderColor','boxShadow'].forEach(p=>{const v=s[p];const m=v.match(/rgba?\\(\\s*(\\d+)[,\\s]+(\\d+)[,\\s]+(\\d+)/);if(!m)return;const t=[+m[1],+m[2],+m[3]];const mx=Math.max(...t),mn=Math.min(...t);if(mx<70||mn>210||mx-mn<45)return;if(ok.some(o=>eq(o,t)))return;sat.push(el.className+'|'+p+'|'+v)});const m2=s.backgroundColor.match(/rgba?\\(\\s*(\\d+)[,\\s]+(\\d+)[,\\s]+(\\d+)/);if(m2){const t=[+m2[1],+m2[2],+m2[3]];if(t[0]>245&&t[1]>230&&t[1]<250&&t[2]<245&&(t[0]-t[2])>8)pink.push(el.className+'|bg|'+s.backgroundColor)}});return JSON.stringify({saturated:sat.slice(0,10),pinkish:pink.slice(0,10),count:sat.length+pink.length})})()
