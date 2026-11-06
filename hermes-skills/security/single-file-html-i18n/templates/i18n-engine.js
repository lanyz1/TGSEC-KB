/* Runtime zh<->en toggle for a single-file HTML app (SPA + hash routing).
   Inject at the very start of <script>. Source HTML stays in ONE language
   (English); zh is applied at runtime. Switching back to en reloads the page
   (restores source => no reverse dictionary, no drift).
   Usage notes:
   - Dictionary keys must be FULL display strings, longest-first is automatic.
   - Demo data (product names, addresses) must be in the dictionary too.
   - Token safety: add whole tokens first (e.g. 'Type-C Fast-charge Cable 100W')
     so word-level keys ('Type') can't clobber them.
   - Wire the topbar selector: <div class="select" id="langBtn" onclick="toggleLang()">English<svg ...>
*/
var I18N = {
  /* 'English text': '中文文本',
     'Dashboard': '工作台',
     'pending shipments': '待发货', ... */
};
var LANG = localStorage.getItem('qavlixor_lang') || 'en';
var _KEYS = Object.keys(I18N).sort(function(a,b){ return b.length - a.length; });
function _escRE(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
function _trAll(v){
  for(var i=0;i<_KEYS.length;i++){
    var k=_KEYS[i], zh=I18N[k];
    var re=new RegExp('(^|[^A-Za-z])'+_escRE(k)+'([^A-Za-z]|$)','g');
    v = v.replace(re, function(mm, pre, post){ return pre + zh + post; });
  }
  return v;
}
function applyLang(){
  if(LANG==='zh'){
    var w=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), nodes=[];
    while(w.nextNode()){ var n=w.currentNode; if(n.nodeValue && /[A-Za-z]/.test(n.nodeValue)) nodes.push(n); }
    nodes.forEach(function(n){ var r=_trAll(n.nodeValue); if(r!==n.nodeValue) n.nodeValue=r; });
    document.querySelectorAll('input[placeholder]').forEach(function(el){
      var r=_trAll(el.getAttribute('placeholder'));
      if(r!==el.getAttribute('placeholder')) el.setAttribute('placeholder',r);
    });
    var btn=document.getElementById('langBtn');
    if(btn && btn.firstChild) btn.firstChild.nodeValue='English';  // now shows the way BACK
  } else {
    location.reload();
  }
  localStorage.setItem('qavlixor_lang', LANG);
}
function toggleLang(){ LANG=(LANG==='en'?'zh':'en'); applyLang(); }
if(LANG==='zh'){ window.addEventListener('DOMContentLoaded', function(){ setTimeout(applyLang, 50); }); }
