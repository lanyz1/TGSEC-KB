# 滑块过闸：真浏览器 + 真鼠标拖拽（完整 recipe）

适用：任何把 `slide` 型人机校验产物（腾讯 `ticket`/`randstr`、极验 `validate`、易盾 `token`、自研 `captcha_token`）
当**闸门凭证**的站点。目标不是「复刻验证码协议」，而是「让页面自己把遥测发出去、把产物写进它自己的表单」。

## 何时走这条

- 端点回笼统码，bundle 显示载荷里有验证码字段，而你只要一发或几十发。
- 弹窗是**站点自己的实例**（单例约束，见 SKILL.md）⇒ 只能借，不能造。
- 要批量/无人值守时改用协议复刻路线（补环境 + 逐轮生成遥测），两条路线的产物契约一样：**同轮、同会话**。

## CDP 事件序列（实测可过）

```python
# 伪码：经你的 CDP 客户端 send() 直发；x0,y0 = 手柄按下点（整图坐标）
def drag(x0, y0, d, n=30):
    send("Input.dispatchMouseEvent", type="mousePressed", x=x0, y=y0,
         button="left", buttons=1, clickCount=1)
    for i in range(1, n + 1):
        t = i / n
        x = x0 + d * (1 - (1 - t) ** 3)        # 三次缓出
        y = y0 + random.uniform(-1.2, 1.2)      # 抖动，避免完美直线
        send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="left", buttons=1)
        time.sleep(random.uniform(0.012, 0.030))
    send("Input.dispatchMouseEvent", type="mouseReleased", x=x0 + d, y=y0,
         button="left", buttons=1, clickCount=1)
```

要点：

- 每个事件都要带 `button`/`buttons`/`clickCount`，否则页面看到的是合成事件（部分厂商会拒）。
- 步间隔**不要等距**；加 1–2 次短停顿更像人。
- 先 `mousePressed` 在**手柄中心**上：起点错 = 拖多远都不对。

## 读图几何（每次标定一次，本轮复用）

1. 截图 → 按弹窗矩形裁剪（`warp.x, warp.y, w, h`）。
2. **拼图块**左缘：白描边矩形；**缺口**左缘：同尺寸的深色实心凹槽 ⇒ `d = 缺口x - 块x`。
3. **手柄中心**：拖动条的圆形/箭头把手，取整图坐标当 `(x0,y0)`。
4. 固定量：拼图块起始左缘 ≈ `warp.x + 45.5`。弹窗几何在同一站点内稳定：
   换页面只整体平移（例：同一站点两个入口页的弹窗 y 相差一个固定偏移）⇒ 重标一次裁剪原点即可。

## 成功判据

- 网络层：`cap_union_new_verify` 回 `errorCode:0`（或对应平台的等价回执）。
- 页面层：**组件表单里产物非空**（`form.ticket`/`form.randstr`）——这才是你要的东西。
- 业务层：拿产物立刻打受控端点，得到业务成功响应（而不是同一句笼统码）。

## 失败复盘顺序

1. 弹窗没动 ⇒ 起点不在手柄上（重新读图取手柄坐标）。
2. 动了但产物空 ⇒ 距离不对（重读缺口，别用上一张图的 dx）。
3. 回 `errorCode` 非 0 ⇒ 事件序列被识别为合成：加步数/加抖动/加停顿，或确认是 headed 真 Chrome。
4. 拿到产物但业务仍拒 ⇒ 八成是产物已被消费/TTL 过期 ⇒ **同一进程一气跑完：取产物 → 发业务请求**。

## 与协议复刻的分工

- 协议复刻 = 批量与无人值守（补 `window`/DOM 环境、逐轮生成 `collect`/`w`/`ans`/`pow`）。
- 真鼠标拖拽 = 过闸取证（零逆向，一分钟内出结果）。
- 两者共用铁律：产物与其 challenge 必须同轮；不跨轮、不跨会话复用。
