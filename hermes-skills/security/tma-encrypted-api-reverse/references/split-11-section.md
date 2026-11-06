## 载具 / 编码 / 通道 —— 判读铁律（负结论前必跑正控）
- ★★ **同一 token 三种载具各吃不同形态，绝不能混用**：`bot /start` 吃**带标签**（`rpl_`/`rpu_`）、HTTP `token=` 只吃**裸载荷**、App `startapp=` 吃**裸载荷**。带错形态的负结果**全部无效**（实测：HTTP 侧带 `rpl_`/`rpu_` 一律 `40671`，换裸载荷当场 `200`）⇒ **任何针对 token 的负结论，先做「同 token × 多载具」正控**，否则九个轮次的探测可能全白跑。
- ★★ **URL-safe base64 载荷必须用 `urlsafe_b64decode` + 补 `=`**：标准 `b64decode(validate=False)` 会**静默丢弃 `-`/`_`** ⇒ 长度 28→22 ⇒ `binascii.Error: Incorrect padding`（表象是「驱动零输出」，极易误判成网络/限流/目标拒绝）。修法：`base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))`，并在解码前打印长度自证。
- ★★ **`DataInvalidError` 有【三种】成因，不可一刀切**（实测纠偏，此前「一律记通道级」过粗）：① **偶发** —— 同一 `menu_swap` 首发生 `DataInvalidError`，**重跑即成功**；② **页上下文不对** —— `pf_bal`/`pf_bills` 在**首页消息**上发必 `DataInvalidError`，在**个人中心页消息**上发 100% 成功；③ **参数真无效** —— `gbh_list:1:all` 成功、换成**本人真实 id** 立刻 `DataInvalidError`（那个 `1` 是**范围常量**而非 user_id）。⇒ 判读纪律：**先按「偶发 / 上下文」重试一次并换对页，再下结论；不得单发即写成「目标防住」**。要测 callback 参数面，只能用键盘上真实存在的 data 值。
- ★ **bot 的 callback 前缀不是 HTTP 路由**：`sw_`/`yb_`/`vas_`/`pf_`/`sc_`/`gbh_`/`mrch_`/`bp_` 这类命名空间在 Mini App API 上实测 **52/52 = 404**（含 `ping` 基线、且同基址下已知存在的 `/rp/detail` 匿名回 401 作阳性对照）⇒ 这些功能由 **bot 侧 handler 独立实现**，不经过 Mini App API；**别拿 callback 名当路由词表去扫**（扫不出东西才是正常的）。
- ★ **bot 导航脚本每步必须显式复位**：每轮结束**无条件** `send_message('/start')` 回家，否则上一步的 `msg` 对象指向子页面 ⇒ 后续菜单全被判「主页无此按钮」而**静默跳过**，输出看起来像「目标没这些功能」—— **这是我方缺陷，必须与目标拒绝区分开再下结论**。
- ★ **`/media/*` 子命名空间枚举用「同基址 404 文案」当 oracle**：不存在=Go 原始 `404 page not found`(18B)、存在=业务码 ⇒ 一次 19 探针即可证明「该命名空间只有一个端点」（实测 `/media/bg` 是唯一存活者，且 `?name=../../etc/passwd` 被忽略——响应字节数与正常**完全相同**即无穿越）。

