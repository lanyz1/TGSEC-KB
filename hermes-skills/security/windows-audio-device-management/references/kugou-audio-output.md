# 酷狗音乐音频输出设置 + computer_use 自绘UI自动化实测 (2026-08)

## 手动设置路径 (酷狗)
1. 主界面右上角 **☰ 主菜单** → **设置**
2. 左侧标签 **音频设置**（注意有"音频设置"标签 + 页面内也有"音频设置"小节标题，别混淆）
3. **音频输出** 下拉框（旁边提示：新设置将在重新播放时生效，输出设备推荐 DirectSound 输出类型）
4. 切歌/重新播放后生效

## 本机音频设备实测 (2026-08-12)
- 蓝牙耳机 **LP90 Pro**：暴露两个端点 `扬声器 (LP90 Pro)` 和 `头戴式耳机 (LP90 Pro Hands-Free)` —— 听歌应选前者
- kX 10k1 声卡 (kxmixer/MX6调音台)：Wave Out 2/3、4/5、6/7、Master Mixer、SPDIF/AC3 Output、Recording Mixer
- 网易虚拟音频设备（扬声器 + 麦克风阵列）
- NVIDIA 虚拟音频设备
- Realtek 高清音频、HDMI 输出：`ConfigManagerErrorCode=22`（被禁用，正常）

## computer_use 驱动酷狗 (自绘UI) 实测教训
酷狗是**自绘UI**，UIA 可访问性树稀疏（大量 Custom/Image 角色、bounds 为 0 的元素），后台点击很不稳定。

### 关键坑
1. **Cua Driver 0.17：裸 element index 点击被拒**
   `click: bare element_index is not accepted in Cua Driver 0.17; pass element_token or snapshot_id with element_index`
   → 自绘UI应用改用 `coordinate=[x,y]` 点击。
2. **坐标系统**：capture 返回的 bounds 是屏幕绝对坐标（Window bounds 即窗口位置）。
   - 歌曲详情页左上角 (窗口内 30,16) = 屏幕 (窗口x+30, 窗口y+16) 是"收起歌曲详情页"按钮
   - 再往左 (窗口内 10,17) 附近是主菜单按钮，点它才出设置
3. **窗口位置会漂移**：后台点击过程中窗口从 (665,233) 漂到 (541,219) 再 (27,269)，所有坐标全部失效 → 每次操作前重新 capture 取 Window bounds。
4. **设置窗口是覆盖层**：打开设置页后点击下拉框等元素，界面易跳回歌曲详情页；自绘UI的 ComboBox 下拉列表选项可能不进 UIA 树。
5. **右键菜单有时能出主菜单**（酷狗音乐-菜单，含"设置"项），但菜单项 bounds 可能在窗口外（屏幕右侧），点击易落空。
6. **vision 模式对酷狗截图可能被辅助视觉 API 拒绝**（image too large / format 不支持）→ 用 som/ax 树 + 坐标兜底。

### 更稳的替代路线（本次最终建议）
- **首选系统级**：`Start-Process 'ms-settings:apps-volume'` → 音量混合器 → 酷狗 → 输出设备选 LP90 Pro。Win11 原生按应用路由，不碰酷狗自绘UI。
- 其次全局默认设备：`ms-settings:sound` 或任务栏喇叭。
- 酷狗应用内设置仅在用户明确要"改酷狗自己的输出"时尝试，且做好多次重试的准备。
