# 外挂功能全谱与注入链（由字节码 + JNI 注册表还原）

## 注入链（把报告里的图固化成可复用模板）

```text
游戏启动 → UnityPlayerActivity System.loadLibrary("ztgame")
  → 假 SDK so 的 JNI_OnLoad（真身可从 .bss 解密后执行）
  → 释放/加载隐藏 dex（InMemoryDexClassLoader / DexClassLoader）
  → ImGui 悬浮窗 + KeyMouseMapper 初始化
  → 键盘轮询线程 + Window.Callback 挂钩 + native 触屏注入器就绪
  → 真实键鼠 → native 层合成 MotionEvent → 注入游戏
  → （自瞄）aimRadius 圈内锁定 → 注入 aimTouchX/Y
  → 卡密到期 → 授权 so QueryStatus 失败 → 功能锁死
```

**为什么一行 dex 不用改**：借的是游戏**本来就有的** `loadLibrary` 调用点。带托管 SDK
（掌趣/腾讯/易盾）的游戏天然会加载同名 so，换掉文件即可随启动自动执行。

## Java 层机制（可跨游戏横向复用）

| 机制 | 实现 |
|------|------|
| 触屏注入 | `InputManager.injectInputEvent(MotionEvent, mode)` 由 native 层发起，绕过 Java 层权限检查 |
| 窗口挂钩 | `KeyMouseMapper$1` 包装原 `Window.Callback`，`dispatchTouchEvent`/`dispatchGenericMotionEvent` 先送外挂再转发 |
| 键鼠映射 | 左键=鼠标位置点击；右键=`shootTouchX/Y` 射击；中键=action2 |
| 键位表 | 16 键 → action 槽位（数字 1-5、E/F/G、Q/R、Tab、空格、F1-F4），`fireKey` sparse-switch 定位 |
| WASD 摇杆 | `synthesizeJoystick` 把方向键状态合成向量，归一化后走 `nativeTouchMove` |
| 键盘轮询 | 独立 `HandlerThread` + 反射隐藏 API `InputDevice.getKeyCodeState`，周期 `POLL_MS` |
| JNI 桥 | `nativeTouchDown/Move/Up`、`nativeVisionWheel`、`nativeGetScreenSize`、`KMPoll`、`KeyConfig` |

**逆向时怎么拿“功能全谱”**：① 隐藏 dex 反编译 → 类/方法/常量字符串
② native 导出符号 + `KeyConfig` 类字段 → 配置键集合 ③ `.data/.rodata` 里的配置键字符串
（`POINTER_*`/`aim*`/`*TouchX/Y`/`POLL_MS`）= 功能开关清单。三者交叉即全景，
不需要完全反汇编 native。

## 自瞄与悬浮窗

- 自瞄配置键：`aimRadius` / `aimTouchX` / `aimTouchY`（圈半径 + 触摸坐标）——**配置键出现
  即说明有自瞄逻辑**，拿这三个值能在游戏内复现搜索范围。
- ImGui 悬浮窗：`GLES3JNIView` 渲染 ImGui 菜单，`tag="imgui_overlay"`；支持多开
  （`addGame/gameMap` 多实例路由）。基于 ImGui 的挂（PUBG 系辅助常见）都长这个形。

## il2cpp 外挂的 native 侧定位（通用四步）

```text
① dl_iterate_phdr / fopen("/proc/self/maps") 找 libil2cpp.so 基址（常连同 libunity.so）
② 从基址取 il2cpp 导出: il2cpp_domain_get / il2cpp_class_from_name /
   il2cpp_class_get_field_from_name / il2cpp_field_get_offset → 拿游戏类字段偏移
③ 读字段值（血量/坐标/状态）→ 这是自瞄/透视的输入源
④ 改字段值或 hook 函数（inline hook: mprotect(页,RWX) + memcpy 写跳转）
```

OLLVM 下静态反编译会失效，但**字符串/导出/配置键不会** —— 先拿四样闭环定性，再上动态。

## 动态补齐（native 静态还原不了时）

```bash
# 1) 枚举 JNI 注册表：native 方法名 ↔ 函数地址（拿到未导出真身）
frida -U -f com.xxx -l jnireg.js      # hook RegisterNatives(env, clazz, methods, n)
# 2) 内存扫隐藏 dex（dex 被加密/无文件时）: Memory.scan(base, size, "64 65 78 0a 30 33 35 00")
# 3) dump 可执行 .bss（JNI_OnLoad 自解密后的真身）
#    Process.findModuleByName("libztgame.so") → Memory.readByteArray(addr, n) → 重建 ELF 落盘
# 4) hook 导出验证协议语义（卡密 so 必做，见 cardkey-so-protocol.md）
```

**诚实边界**：静态只给到「JNI 接口定义 + 字符串证据 + 导入画像」就不算完整 native 还原，
交付文里必须把它写成**动态补齐路径**，不许编造 C 源码。

## 检测面（防守视角，也用于判断外挂是否在跑）

| 面 | 检测点 |
|----|--------|
| 文件 | `lib/<abi>/` 同名 so 与官方包 hash 不一致；出现无对应 smali 的 so |
| 加载 | `loadLibrary` 的 so 内部字符串与 SDK 真身不符；`.bss` 可执行（`/proc/self/maps` rwx 匿名段） |
| 进程内 | 多出 `imgui_overlay` 的 Window/GLSurfaceView；非游戏线程的键盘轮询 |
| 输入 | 同一帧出现非触摸屏源的 MotionEvent；`injectInputEvent` 调用栈 |
| 内存 | 匿名 rwx 段、模块列表与 `/proc/self/maps` 不一致（linker 绕过的痕迹） |
| 授权 | 卡密 so 导出名族 `*InitCardKey/*Login/*QueryStatus` |
