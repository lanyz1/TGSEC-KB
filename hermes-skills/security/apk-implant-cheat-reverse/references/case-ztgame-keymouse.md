# 案例：com.ztgame.bob 19.6.7 内置外挂（KeyMouse 键鼠映射 + 自瞄）

目标：Unity il2cpp 手游包，123MB，versionName 19.6.7。
结论：内置外挂 = **KeyMouse 键鼠映射器改造版（含自瞄配置）**，纯 so 替换式植入。

## 时间线铁证

| 文件 | mtime | 判定 |
|------|-------|------|
| 游戏本体 so/dex/assets | 2026-05-26 | 原始构建 |
| `lib/arm64-v8a/libztgame.so` | **2026-09-12 16:02** | 外挂本体，伪装掌趣 SDK（后塞） |
| `lib/arm64-v8a/libbypass.so` | **2026-09-12 16:03** | 卡密验证模块（后塞） |
| `META-INF/*` 签名 | 2026-09-12 16:03 | 重打包签名 |

三分钟内完成「换 so + 塞卡密模块 + 重签」——**同分钟聚类 + 与本体差 3.5 个月** = 植入实锤。

## 三件套

1. **libztgame.so（本体）**：真身据源文件名 `KeyMouseMapper.java`/`GLES3JNIView.java`/`ImGui.java`
   （零掌趣 SDK 特征）；导出 `AceProvideJavaVmV1`（腾讯 ACE 标准导出名）骗过加载器/反作弊；
   内嵌 **27KB dex @0x63fae0，13 类**；导入 `dlopen/dlsym/dl_iterate_phdr`（找 il2cpp 基址）、
   `mprotect/memcpy`（inline hook）、`sigaction/fork/waitpid/getppid`（反调试）、`getauxval`（linker 基址）；
   配置键全集：`POINTER_ACTION1~8`/`POINTER_AIM`/`POINTER_FN1~4`/`POINTER_JOYSTICK`/`POINTER_SHOOT`/
   `POINTER_SLOT1~5`/`POLL_MS`/`aimRadius`/`aimTouchX,Y`/`shootTouchX,Y`/`action1~8TouchX,Y`；
   OLLVM + JNI_OnLoad 本体在 `.bss` 运行时解密。
2. **libbypass.so（授权）**：7 个 `atomBypass*` 导出；三步协议
   `InitCardKey → Login → QueryStatus`（+ Begin/CompleteKeyExchange 握手）；内部含手工 ELF 解析
   （`e_phoff` 检查、`symbol not found`）→ linker 绕过/符号劫持；OLLVM + 跳板分发。
3. **隐藏 dex（13 类）**：`com.example.keymouse.KeyMouseMapper`+`$0~$4`+`$KeyConfig`、
   `com.example.imgui.ImGui`+`$0~$3`、`GLES3JNIView`。Java 侧配套 `com.ztgame.bob.BobMD5`
   → `System.loadLibrary("BOBMD5")` + native `encryptByMD5`（BOBMD5.so 未随包，运行时释放）。

## 功能全谱

键鼠映射（native 合成触屏）/ 左键=点击·右键=射击·中键=action2 / WASD 摇杆合成 /
16 键位映射 / 自瞄（aimRadius 圈）/ ImGui 悬浮窗（`tag="imgui_overlay"` 多实例）/ 
Window.Callback 拦截 / 独立线程键盘轮询（反射 `InputDevice.getKeyCodeState`）。

## 复现命令

```bash
python3 scripts/apk_implant_probe.py apk --path com.ztgame.bob_19.6.7.apk --analyze-so
python3 scripts/apk_implant_probe.py so --path lib/arm64-v8a/libztgame.so --dump-dex out/
jadx -d src out/libztgame_0x63fae0.dex
```

## 边界（诚实交代）

native 层因 OLLVM + `.bss` 解密无法静态完整还原 → 只给 JNI 接口定义、字符串证据、导入画像；
补全走 Frida attach il2cpp（见 `cheat-mechanics.md` 的动态补齐节）。**不得编造 C 源码。**
