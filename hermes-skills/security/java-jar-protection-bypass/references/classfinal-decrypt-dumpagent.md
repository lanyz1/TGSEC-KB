# ClassFinal 加密 jar 解密 — 目标机双 agent dump 法 (完整配方)

2026-10 实战: pack-2.10.0.jar (154MB, 97 构建母机) 138 类 dump → CFR → 127 java 源码 (案卷 /root/cases/drfmud7h5b2n)。

## 识别
- jar 内 `META-INF/.classes/` 集中放加密 .class; 类引用 JarDecryptor/EncryptUtils/CoreAgent
- 启动命令行: `-javaagent:/path/app.jar='-pwd <口令>'` — 口令常裸在 `ps aux | grep java` / start.sh; 同系统多机同一把 (实测 97/144 同款口令)
- javap 可看解密器流程, 但离线复现必死 (机器码绑定)

## ✘ 失败路 (别重复)
- 本地(或无绑定关系的机器)直接调 JarDecryptor.doDecrypt / 自写 DecAll 批量解密 → 253 类全 fail: 机器码绑定, 解密只在运行机成立

## ✔ 可用路: 目标机双 agent dump (实测 138 类)
1. 拿口令: `ps aux | grep java` 或启动脚本
2. 写 DumpAgent.java (下), 目标机 JDK 编译 + 打 jar (Manifest: Premain-Class: DumpAgent)
3. 改服务启动参数: 在**原 ClassFinal agent 之后**追加 `-javaagent:/tmp/dumpagent.jar`
   (transformer 链式: 前者先解密, 后注册的 dump agent 拿到解密后的 classfileBuffer)
4. 重启服务 → 触发功能面加载类 → 收集 dump 目录
5. 回本地重排目录树 (点号类名 → 包目录) → CFR 反编译
6. 完事还原启动参数

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

## 覆盖与限制
- dump 覆盖 = 只含**被加载过**的类; 懒加载类缺失 (实测 frezrik 包从未加载→抓不到, 实为开源 AXML 工具, 价值低) → 触发功能面扩大覆盖
- 目标机 JDK 版本编译 agent 最稳 (JDK1.8 目标机实测 OK); 本地 java17 + cfr-0.152 反编译

## 战果 (pack-2.10.0.jar)
- 138 类 → CFR → 127 java 源码: AppTaskMananger(打包全流程)/JiaguServiceOptimized/OssController(FtpStorageImpl,FtpUtil)/LicenseController(SSRF 面)/ConfigService(fix 域)
- 源码结论: JWT 密钥=启动随机 UUID; oss/test=SSRF 面; ZIP 伪加密有效期到 2027
