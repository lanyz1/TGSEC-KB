# IP → 域名反查：纯 IP 证书目标的身份归属

**何时用**：应用正面已被逐条验证打光（鉴权/注入/绕过/走私/文件/限流全灭），继续换端点收益趋零。
此时该换的是**视角**而不是另一个端点 —— 从「攻应用」换成「查是谁」。
本卡是 `references/hidden-origin-recon.md`（域名→源站 IP）的**镜像方向**：给一个裸 IP，反推出它藏起来的域名与运营者身份。

> 用户不接受「没有办法了」这种结论。**正面打光必须换视角，不是宣布结束。**

## 起点特征（命中即该走这条路）

- 只在裸 IP 上提供 HTTPS，且证书是 **Let's Encrypt 纯 IP 证书**
  （`Subject:` 空、`Subject Alternative Name: IP Address:x.x.x.x`、有效期仅 6 天 = 自动续期）
- 所有 Host 头变体（`localhost` / 乱填 / 后来反查到的子域）都返回**同一个应用**
- 反向 PTR 只有机房名（`static-x-x-x-x.dsl.<isp>.net`），无业务线索
- `whois` / `crt.sh` 按域名查全空

⇒ 这是**主动隐匿域名**，不是「没有域名」。做正向查询必然全空，必须反向。

## 执行顺序（三步，实测各一发有效）

### 1. FOFA 反查 IP —— 一发定胜负

```
qbase64 = base64('ip="1.2.3.4"')
fields  = host,domain,title,ip,port,server,icp,os&size=100
```

一次返回三层情报：

| 字段 | 收获 |
|---|---|
| `title` | 同机**每个服务**的标题（历史暴露面） |
| `domain` | 该 IP 历史上绑过的**真实域名** ← 本步核心产出 |
| `port` + `server` | 历史端口与 Web 中间件指纹 |

实测（某裸 IP 收款后台）：一次拿到 15 条，直接暴露运营者的历史栈——
`code-server login` / `ChatGPT 号池管理` / `Grok2API` / `Sub2API - AI API Gateway` / `PostgreSQL`，
外加域名。**业务定性当场成形。**

> ⚠️ **端口必须复核，域名不用复核。** 端口字段是历史快照：TCP 连上收 **RST**（nmap `closed`）= 真没了；
> **超时**（nmap `filtered`）= 有墙、服务可能还在。`nmap -sA` 回 `unfiltered` 可佐证
> 「不是墙丢包，是真没监听」。实测那些端口全已下线，但 `domain` 和 `title` 依然是你最值钱的两列。

### 2. crt.sh 拖子域 —— 业务形态一眼定性

```bash
curl -s "https://crt.sh/?q=%25.<域名>&output=json" | jq -r '.[].name_value' | sort -u
```

实测 24 张证书还原出 11 个子域，**光看名字就能定业务**：
`www`=New API、`admin`=CLI Proxy 管理台、`sub`=Sub2API、`grok`=Grok2API、
`claude`/`gpt`/`gpt2api`/`flow`/`api`/`code`/裸域。
⇒ 运营者 = AI API 中转站/号池转卖商；而被告知的那个「收款记账后台」
**只是它的营收发卡后端**（收款核销 + 卡密自动发货 + TG Bot + 设备管理）。
**这个定性修正比任何单点漏洞都值钱。**

### 3. 回打子域验证 vhost（本步常用来「关路」）

```python
requests.get(f"https://{IP}/login", headers={"Host": sub}, verify=False)
```

实测 11 个子域**全部**路由到同一个应用，且 `dig NS MX TXT SOA` 全空、AXFR 拒绝、
SOA 序列显示 zone 在一个月前刚被清过 ⇒ 判定「域名是历史遗留，当前单应用裸跑」，
**别在 vhost 面继续投入**。**能关掉一条路和找到一条路同样省时间。**

## 复核与收尾命令

```bash
for p in 22 80 443 3000 5432 8000 8080 8088 18080; do
  timeout 6 bash -c "echo >/dev/tcp/<IP>/$p" && echo "$p OPEN" || echo "$p closed"
done
nmap -Pn -sA -p 3000,8080,5432 <IP>     # unfiltered = 不是墙丢包，是真没监听
dig NS MX TXT SOA CAA <域名> @8.8.8.8    # 全空 = zone 已被清理
dig @<ns> <域名> AXFR                    # 0 行 = 拒绝传送（正常）
```

## 免费反查源（按可用性排序，别在一个源上卡死）

| 源 | 状态 |
|---|---|
| FOFA `ip=` | **主力**，带 title/domain/port 三列，一发够用 |
| `crt.sh/?q=%25.<域名>&output=json` | 子域还原主力（偶尔 502，重试） |
| `api.hackertarget.com/reverseiplookup/?q=<IP>` | 兜底，常只回 PTR |
| `rapiddns.io/sameip/<IP>?full=1` | 兜底，抓 `<td>域名</td>` |
| `webscan.cc` / `viewdns.info` / `threatminer` / `dns.bufferover.run` | **常 502/403/超时，别卡在这里** |

顺带：`whois <域名>` 不返回时试 `curl https://rdap.org/domain/<域名>`；域名彻底删除则 RDAP/WHOIS 全空，**到此为止不要纠缠**。

## 这类情报怎么用（写进报告的三件事）

1. **报告定性**：把「一个 IP 上的神秘后台」升级成「某某运营者的营收后端」，
   附历史服务面佐证其安全习惯。
2. **解释为什么打不进**：历史弱面已全部撤除 → 攻击面收敛到单一加固应用 ⇒
   「正面无解」是**已被验证的结论**，不是「我没找到」。
3. **给出下一步现实路径**：从运营者侧（TG 客服/代理）取凭据；或长期监控该应用新端点
   （schema/version 仍在迭代 = 新功能 = 新攻击面）。

## 别把「找不到」写成失败

- 目标代码不开源时，`grep.app` / `searchcode.com` / GitHub 搜特征串会**全 0 命中**：
  这是「找不到同款产品的其它部署」的**结论**，不是搜索失败。
  **搜之前先想清「找到同款能拿来干什么」**，不值得就别花时间。
- 域名子域全回同一个应用、DNS 全空，不代表这一轮白跑 —— 它把「域名/vhost」整条线判死了，
  下次同类目标可以直接跳过这一步。
- 需要临时批量查询时，可直接 curl `https://html.duckduckgo.com/html/?q=<词>` 走已配置代理
  取结果标题与 URL（正则 `result__a" href="([^"]+)"`）。
