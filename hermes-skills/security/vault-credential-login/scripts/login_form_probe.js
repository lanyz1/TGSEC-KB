// 登录页表单探针：用 browser_exec 里的 js(...) 执行
// 作用: 取表单 action / 输入框(name,id,type,值长度,placeholder) / 按钮归属哪个 form / 页面错误文案
//      默认顺手清空一个字段（#otp），只读时把 noClear 置 true
// 输出只给值长度，不回显可能含秘密的值
(() => {
  const noClear = (typeof NO_CLEAR !== 'undefined') ? NO_CLEAR : false;
  const clearSel = (typeof CLEAR_SEL !== 'undefined') ? CLEAR_SEL : '#otp';
  const out = { url: location.href, origin: location.origin, forms: [], inputs: [], buttons: [], errs: [] };
  document.querySelectorAll('form').forEach(f => out.forms.push({
    action: f.getAttribute('action'), method: f.method, id: f.id, cls: (f.className || '').slice(0, 60)
  }));
  document.querySelectorAll('input, textarea').forEach(i => out.inputs.push({
    name: i.name, id: i.id, type: i.type,
    value_len: (i.value || '').length,
    placeholder: i.placeholder || '',
    maxlength: i.maxLength, required: i.required
  }));
  document.querySelectorAll('button, input[type=submit], [role=button]').forEach(b => out.buttons.push({
    text: (b.innerText || b.value || '').trim().slice(0, 30), type: b.type, name: b.name, id: b.id,
    form: b.closest('form') ? (b.closest('form').getAttribute('action') || 'inline') : 'none'
  }));
  document.querySelectorAll('.flash-error, .flash-warn, .flash-success, [role=alert], .error, p.color-fg-danger')
    .forEach(e => { const t = (e.innerText || '').trim(); if (t) out.errs.push(t.slice(0, 300)); });
  if (!noClear) {
    const el = document.querySelector(clearSel);
    if (el) { el.focus(); el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); out.cleared = clearSel; }
    else { out.cleared = null; }
  }
  return JSON.stringify(out);
})()
