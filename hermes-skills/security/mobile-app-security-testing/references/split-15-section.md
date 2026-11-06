## 十四、工具链

```bash
# ========== Android ==========
jadx / jadx-gui            # Java反编译(首选)
apktool                    # APK解包/重打包
frida + frida-tools        # 动态Hook/抓包/脱壳
objection                  # 免root快速评估(sslpinning/root/hooking)
frida-dexdump              # 内存DEX提取
FART (hanbinglengyue)      # 主动调用脱壳(定制ROM)
BlackDex / DexExtractor    # Xposed拖拽脱壳
HLuda                      # 魔改版Frida(反检测)
Ghidra / IDA Pro          # Native so逆向
unidbg                     # so模拟执行(PC端trace/算法还原)
drozer                     # 组件攻击(Content Provider/Intent)
MobSF                      # 自动化静态/动态分析(一键报告)
r0capture                  # Frida SSL明文抓包
Play Integrity API测试工具  # 认证绕过辅助
Magisk / LSPosed / Zygisk   # Root/模块体系(DenyList/隐身)
frida-dexdump              # 内存DEX提取

# ========== iOS ==========
class-dump / swift-class-dump # ObjC/Swift类导出
Hopper / IDA Pro / Ghidra    # Mach-O逆向
frida-ios-dump               # 越狱砸壳
dumpdecrypted                # 传统砸壳
objection                    # sslpinning/jailbreak/keystore
LLDB / debugserver           # 动态调试
SSLKillSwitch2               # 系统级pinning绕过(Cydia插件)
iMazing / libimobiledevice   # 设备管理/备份提取
Cycript / Theos / Logos      # 运行时修改/tweak开发
Corellium                    # 云端虚拟iOS真机
keychain_dumper              # Keychain提取

# ========== 抓包/网络 ==========
Burp Suite                   # HTTP/WebSocket代理(主力)
mitmproxy / mitmweb          # 脚本化代理
Wireshark                    # TLS解密/私有协议分析
Charles / Proxyman           # 移动端友好代理
r0capture                    # Frida SSL明文输出
pcileech / proxychains       # 内存/代理进阶

# ========== 跨平台/小程序 ==========
Blutter (worawit)            # Flutter Dart AOT逆向(首选)
reFlutter                    # Flutter反混淆/重打包
hermes-dec / hbcdump         # React Native Hermes字节码反编译
wxappUnpacker / wxapkg解密    # 小程序解包(需配合内存dump取密钥)
Ghidra脚本(DeFlat等)         # 反混淆/去平坦化

# ========== AI辅助 ==========
LLM (GPT-4o/Claude/Gemini等) # 反编译代码审计/脚本生成/调用链分析
Ghidra + LLM插件             # 反编译结果直连LLM分析
semgrep / mobsf + AI分析      # 规则扫描+AI归因

# ========== 自动化平台 ==========
MobSF                        # 一键静态+动态报告
QARK / Needle                # iOS自动化审计
Drozer                       # Android组件攻击框架
Frida Console / objection    # 交互式Hook
```

