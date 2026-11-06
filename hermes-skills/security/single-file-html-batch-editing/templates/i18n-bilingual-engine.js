/* i18n bilingual engine for single-file HTML prototypes.
   Inject right after the opening <script> tag; make the top-bar language control
   call toggleLang(). Source HTML stays in ONE language (English):
   - switch to ZH mutates text nodes at runtime (word-boundary, longest-key-first)
   - switch back to EN = location.reload() (source untouched, no reverse mapping)
   - choice persists in localStorage.
   Verified on Qavlixor seller console (378-entry dict, 17 views + 18 modals). */

var I18N = {
  /* EN -> ZH. Longest keys matter: put full compounds FIRST so longer strings
     win over shorter ones (e.g. "Type-C Fast-charge Cable 100W" before "Type",
     "Shipping Templates" before "Ship"). Order inside the object is irrelevant —
     keys are re-sorted longest-first at load. */
  "English": "简体中文",
  "Dashboard": "工作台",
  "Today's Sales": "今日销售额",
  "pending shipments": "待发货",
  /* ... fill the rest of the dict from your baseline's visible strings ... */
};

var LANG = localStorage.getItem('app_lang') || 'en';
var _KEYS = Object.keys(I18N).sort(function(a, b) { return b.length - a.length; });

function _escRE(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function _trAll(v) {
  for (var i = 0; i < _KEYS.length; i++) {
    var k = _KEYS[i], zh = I18N[k];
    /* word boundary: key must not be flanked by A-Za-z (protects Type inside Type-C,
       Ship inside Shipping). Pre/post chars are preserved. */
    var re = new RegExp('(^|[^A-Za-z])' + _escRE(k) + '([^A-Za-z]|$)', 'g');
    v = v.replace(re, function(mm, pre, post) { return pre + zh + post; });
  }
  return v;
}

function applyLang() {
  if (LANG === 'zh') {
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT), nodes = [];
    while (w.nextNode()) { var n = w.currentNode; if (n.nodeValue && /[A-Za-z]/.test(n.nodeValue)) nodes.push(n); }
    nodes.forEach(function(n) { var r = _trAll(n.nodeValue); if (r !== n.nodeValue) n.nodeValue = r; });
    /* placeholders */
    document.querySelectorAll('input[placeholder]').forEach(function(el) {
      var r = _trAll(el.getAttribute('placeholder'));
      if (r !== el.getAttribute('placeholder')) el.setAttribute('placeholder', r);
    });
    /* lang button label shows the OTHER language */
    document.querySelectorAll('.select[id="langBtn"]').forEach(function(el) {
      if (el.firstChild) el.firstChild.nodeValue = 'English';
    });
  } else {
    location.reload(); /* source is English — refresh restores it */
  }
  localStorage.setItem('app_lang', LANG);
}

function toggleLang() { LANG = (LANG === 'en' ? 'zh' : 'en'); applyLang(); }

if (LANG === 'zh') {
  window.addEventListener('DOMContentLoaded', function() { setTimeout(applyLang, 50); });
}
