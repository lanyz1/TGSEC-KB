---
name: java-jar-protection-bypass
description: Use when ClassFinal 加密 jar 解密(双 agent dump).
version: 1.0.0
license: MIT
platforms: [linux]
---

# Java jar 加密保护绕过 (ClassFinal 系)

授权目标/授权样本上的加密 jar 解密。2026-10 实战: pack-2.10.0.jar (154MB) 138 类 dump → CFR → 127 java 源码 (案卷 /root/cases/drfmud7h5b2n)。

## 识别 (30 秒)
- jar 内出现 `META-INF/.classes/` 目录(集中放加密 .class; 正常 jar 无此目录) → ClassFinal 系
- 类名: JarDecryptor / EncryptUtils / CoreAgent / ClassFinal
- 进程命令行: `-javaagent:/path/app.jar='-pwd <口令>'` — 口令常裸在 `ps aux | grep java` / start.sh; 同一系统多机常同一把, 动手前先捞

## ✘ 失败路 (别浪费一轮)
- 直接调 JarDecryptor.doDecrypt / 自写 DecAll 批量离线解密 → 全 fail: 机器码绑定, 解密只在运行机成立
- javap 反编译解密器只能看清流程, 离线复现同样死

## ✔ 可用路: 目标机双 agent dump
原理: javaagent transformer 链式 — 原 ClassFinal agent 先解密, 后注册的 dump agent 拿到解密后的 classfileBuffer。

1. 拿口令: `ps aux | grep java` / 启动脚本
2. 写 DumpAgent (下) → javac + jar (Manifest Premain-Class)
3. 目标机服务启动参数尾部追加 `-javaagent:/tmp/dumpagent.jar` (必须在 ClassFinal agent 之后)
4. 重启服务 → 触发功能面(登录/上传/配置页)加载类 → 收 dump 目录
5. 重排目录树 → CFR 反编译
6. 还原启动参数(原样恢复)

```java
// DumpAgent.java
import java.lang.instrument.*;
import java.security.ProtectionDomain;
import java.io.*;

public class DumpAgent {
    public static void premain(String args, Instrumentation inst) {
        final String[] prefixes = {"com/hoo/"};           // 目标包名(slash 形式), 按需多条
        final File outDir = new File(System.getProperty("dump.dir", "/tmp/dumpagent"));
        outDir.mkdirs();
        inst.addTransformer(new ClassFileTransformer() {
            public byte[] transform(ClassLoader l, String name, Class<?> c,
                                    ProtectionDomain pd, byte[] buf) {
                if (name != null) {
                    for (String p : prefixes) {
                        if (name.startsWith(p)) {
                            try {
                                File f = new File(outDir, name + ".class");
                                f.getParentFile().mkdirs();
                                try (FileOutputStream fos = new FileOutputStream(f)) { fos.write(buf); }
                            } catch (Exception ignored) {}
                            break;
                        }
                    }
                }
                return null; // 不修改字节码
            }
        });
    }
}
```

```bash
javac DumpAgent.java
printf 'Premain-Class: DumpAgent\n' > M
jar cfm dumpagent.jar M DumpAgent.class
# 目标机: 启动参数追加 -javaagent:/tmp/dumpagent.jar (在 ClassFinal agent 之后), 重启服务
# 本地收包后重排目录树 + CFR:
python3 - <<'EOF'
import os, shutil
src, dst = '/tmp/dump', '/tmp/retree'
for root, _, files in os.walk(src):
    for f in files:
        if not f.endswith('.class'): continue
        rel = os.path.relpath(os.path.join(root, f), src)
        name = rel[:-6].replace('.', '/')   # 兼容 com.hoo.X.class 与 com/hoo/X.class
        t = os.path.join(dst, name + '.class')
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copy(os.path.join(root, f), t)
EOF
java -jar cfr-0.152.jar /tmp/retree --outputdir /tmp/dec_src
```

## Pitfalls
- dump 覆盖 = 只含被加载过的类: 懒加载类缺失 → 重启后触发更多功能面扩大覆盖; 从未加载的包(先判价值)抓不到
- agent 用目标机 JDK 版本编译最稳 (JDK1.8 目标机实测 OK); 本地 java17 + cfr-0.152 反编译
- CFR 前必须重排目录树 (flat 点号类名先还原包结构, 否则反编译失配)
- 完事还原启动参数; dump agent 返回 null 不改字节码, 低风险
- 源码结论别乱推: 如 JWT 密钥=启动随机 UUID 则不可静态伪造, 别在此耗时间

## 交接
- Windows 网络验证/卡密(天盾/fndata/Nuitka/PyInstaller) → `net-license-crack`
- .NET → `dotnet-reverse`; Go → `go-binary-reverse`; 通用二进制 → `full-reverse`
- 完整配方/环境记录 → `references/classfinal-decrypt-dumpagent.md`
