## initData 时效铁律
- initData **单次使用 + 短时效**,且 `auth_date` 会被 Telegram 缓存 → 「现场铸新 → 立即打」,不能缓存复用。
- 失效码(40704 之类)≠ 签名错。区分:**未握手=40710,签名错=40703,已失效=40704,会话伪=40705**。
- ★★ **initData 四阶鉴权自证阶梯(判别式,必跑)**:同一路径依次送 `无 initData` / `陈旧 initData` / `现铸 initData` / `同一张再送一次`,看错误码落在哪一阶 —— `40701 登录状态无效`(无凭据) → **`40702 登录状态已过期`(★ 签名【已通过】,仅新鲜度不过)** → **`40710 安全信道未建立`(★★ initData 鉴权【已通过】,只差 ECDH 会话)** → `40704 请求已失效`(握手处已消费该 initData)。**只要能看到 40710,就证明凭据链没问题、剩下的纯是协议问题**,不要在爆破/换号/换面浪费轮次。实测新鲜度窗口 **< 2.77h**(2.77h 的 initData 已判 40702)。
- ★★ **必须「铸币 + 握手」在同一进程内一气呵成**:handshake 会**消费** initData(同张再握 ⇒ `40704`),而握手成功后靠 `X-Session-Id` + HMAC 签名维持会话 ⇒ **`RequestAppWebView` 现铸 → 立即注入 → 立即握手**(initData 龄 <30s),再复用该 session 打后续接口。会话 **TTL 实测 `expires_in: 900`(15min)**,过期重铸即可(变 `platform` 无限续期)。
- ★ **initData 注入载具**:本地 `write_file`/Python 生成「已注入的 run 脚本」→ SFTP 上传到跳板机执行(值不进对话、不进 `ps`/history);**绝不用 `sed`**,并做 `content.count(raw)==1` 逐字回验。跳板执行器是 Python 脚本时,子进程必须用 `sys.executable` —— 裸 `"python"` 会解析到无 paramiko 的另一份解释器(Python312)而 `ModuleNotFoundError: paramiko`。
- **续期技巧:变 `platform`/`start_param` 强制 Telegram 铸全新 initData,可无限续期**。
- ★ **注入 initData 绝不能走 `sed`**:替换串里的 `&` 会被展开成整个匹配串,而 initData 含 5 个 `&` ⇒ 静默污染,服务端只回**误导性的 `40701 登录状态无效`**(看着像时效/已用问题,极易误判,白费一整轮)。用 Python 注入 + **注入后逐字回验**(`content.count(raw) == 1`)。

