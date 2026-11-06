## 第 3 步: TG Web K 版驱动要点(大量实测坑)
- `location.hash = '#@bot'` **不切换聊天**;K 版需点左上搜索框输入 @名字→点结果;点错会进 typosquat 山寨 bot(核对 users 数与标题)
- JS `element.click()` 不触发 React 合成事件 → 用 CDP `Input.dispatchMouseEvent`(mousePressed/mouseReleased)在按钮 `getBoundingClientRect()` 中心真实点击
- 按钮 y 坐标为负 = 在虚拟滚动区外;先 `Input.dispatchMouseEvent type=mouseWheel` 滚到消息最底,再取最新键盘按钮坐标
- 历史消息键盘与实时键盘 DOM 重叠 → 取坐标前先滚到底并核对是「最新一条消息」的按钮
- 输入框填 URL/文本后 Enter **不发送**(K 版自定义 keydown)→ 点发送按钮,或让用户手按 Enter(最省事)
- 「Translate to English」等浮条会压住按钮 → JS 移除对应 DOM 容器再点
- 顶部安全弹窗(新登录确认)用 JS `remove()` 掉,别点按钮(会触发安全限制)

