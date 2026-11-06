# so 替换式植入取证 · 三件套细节

## ① 包级指纹

```bash
apktool d -s -f target.apk -o apk_raw        # -s: 不反编译 dex（先看结构）
unzip -l target.apk | grep -E '\.so|classes|\.dex|META-INF'
unzip -l target.apk | awk '{print $1,$2,$3,$4}' | sort | uniq -c | sort -rn
```

看四样：`lib/<abi>/*.so` 名单、`assets/` 里有没有 `.so/.dex/.jar/.dat`、`classes*.dex`
数量（正常 Unity 包 1~3 个）、`lib/` 里是否出现**同名不同源**的 so（替换痕迹）。
Unity il2cpp 正常包必有 `libil2cpp.so` + `libunity.so`；出现托管 SDK 名（如`libztgame.so`）
就在 `smali`/`manifest` 里 grep 谁 `loadLibrary` 它。

## ② 时间线取证（最快出铁证）

```bash
# zip 条目时间（含 lib/ 与 META-INF）
python3 scripts/apk_implant_probe.py apk --path target.apk
# 解包后的真实 mtime（apktool 会丢部分，优先用原始 zip 条目）
find apk_raw -name '*.so' -printf '%T+ %10s %p\n' | sort
```

判读模板：

| 现象 | 判定 |
|------|------|
| 游戏 so/dex 同日同时段，植入 so 晚数月 | 植入实锤（本案例：本体 05-26，植入 09-12） |
| 两个可疑文件时间相差 ≤ 1 分钟，且紧随其后 META-INF 重签 | 同一次重打包（16:02 本体 / 16:03 卡密 + 签名） |
| 全部条目同一时间（如 1981-01-01） | 时间戳被归一化（apktool/AS），**时间线失效** → 走替代证据 |

**时间线失效时的替代证据（本机实测 v2rayNG 就是这种）**：

1. **签名块证书**：v2 签名块 / `META-INF/*.RSA` 的签名者 CN、证书有效期 —— 重打包必然换证书，与原发行商 CN 不同即为二次签名。
2. **ELF 构建痕迹**：`.comment`（clang/NDK 版本）、`.note.android.ident`（NDK build 号）、
   `__DATE__/__TIME__` 残留字符串、`.go.buildinfo`（Go 包还能直接读模块/依赖）。
3. **产物存在性**：内嵌 dex 本身就是决定性证据（原版掌趣 SDK 不会把自己的 Java 层藏在 so 里）。
4. **节区/符号规模对比**：与原版同名 so（同版本 APK）对比节区集合、导出数、`.text` 熵。

## ③ 真身鉴别（“假 SDK”怎么定死）

四样拼图，缺一別下结论：

| 维度 | 命令/字段 | 假 SDK 特征 |
|------|-----------|-------------|
| 源文件残留 | `strings -a x.so \| grep -E '\.(java\|cpp\|c)$'` | 只剩外挂源文件名（`KeyMouseMapper.java`/`ImGui.java`），零 SDK 特征 |
| 导出符号 | 探针 `导出` / `readelf -sW \| grep FUNC.*GLOBAL` | 保留原 SDK **标准导出名**（`AceProvideJavaVmV1`=腾讯 ACE）却是外来实现 |
| 节区集合 | 探针 `节区:` | 缺原 SDK 应有节区 / 异常小 `.text` + 大 `.bss`（运行时解密） |
| 导入画像 | 探针 `[!] hook/加载能力`、`[!] 反调试面` | 见下表 |

导入画像 → 能力推断（**只是线索**，须与其它三样合判；正常 VPN/加解密库也带 fork/dlopen）：

| 导入 | 用途 |
|------|------|
| `dlopen/dlsym/android_dlopen_ext` | 偷加载模块（隐藏 dex / 二次 so） |
| `dl_iterate_phdr` | 遍历模块列表找 `libil2cpp.so` 基址（il2cpp 外挂标配） |
| `mprotect + memcpy` | inline hook（改页属性后写指令） |
| `sigaction/fork/waitpid/getppid/ptrace/prctl` | 反调试/看门狗/防 dump |
| `getauxval` | 取 linker 基址，绕过 `/proc/self/maps` 检查 |
| `__system_property_get` | 读 `ro.build.*` 做环境指纹/模拟器检测 |

## ④ 隐藏 dex 提取

```bash
python3 scripts/apk_implant_probe.py so --path libztgame.so --dump-dex out/
jadx -d src out/libztgame_0x63fae0.dex     # 类清单 + 字节码
```

dex header 关键字段（均 LE）：magic `dex\n035\0` / `file_size`@0x20 / `header_size`@0x24 /
`map_off`@0x34 / `string_ids_off`@0x38。脚本 `DEX_MAGICS` 已覆盖 035~039。

**dex 被加密（找不到 magic）时**：Android 8+ 有 `InMemoryDexClassLoader`，dex 可能只以密文
躺在 `.data/.rodata` → attach 后在内存里扫 magic（Frida `Memory.scan`），或在
`InMemoryDexClassLoader/BaseDexClassLoader` 构造参数处 dump。样本案例 dex 未加密，静态切片即可。

## ⑤ 陷阱

- **stripped so 节区可能不可用**：节区头被剔后只能读 `PT_DYNAMIC`（探测会显示“节区:空”）→
  别据此判定“无导出”；改用 Android 自带 `readelf`（termux/ndk）或 LIEF。脚本的 ELF 解析依赖节区头。
- `.symtab` 与 `.dynsym` 都读，导出取并集；但**只有 `.dynsym` 的名字才对外可见**（可被 dlsym 到）。
- 反汇编前先看熵：`.text` 熵 > 7.2 且节区名异常 = 壳/OLLVM，别浪费时间静态还原。
- 伪装对象不限 ACE：还有掌趣/网易易盾/阿里聚安全/Play Integrity 同名导出。
