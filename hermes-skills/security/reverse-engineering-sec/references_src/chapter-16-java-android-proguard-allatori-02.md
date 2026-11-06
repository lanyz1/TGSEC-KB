### 16.5 ProGuard/Allatori 反混淆

**反编译器对比**:CFR 控制流还原能强(支持 Java 8+ lambda);Procyon 泛型还原准确;JD-GUI 速度快但对复杂控制流易出错;Vineflower(Fern 续作)质量稳定。

**字符串解密**:Allatori 的字符串解密器是静态方法(名为 `_m...`),接收 `int` 返回 `String`,定位后可批量反射调用还原,将 `invokestatic` 替换为 `ldc` 明文。

**反映射恢复**:ProGuard 生成 `mapping.txt`(发布时通常删除),可通过 **Soot 框架**分析调用图与字符串引用,结合已知库 API 签名匹配半自动恢复类名。例如混淆类 `a.b.c` 频繁调用 `android.app.Activity` 方法,可推断其继承自 `Activity` 并重命名。

```bash
# CFR 命令行批量反编译
java -jar cfr.jar target.jar --outputdir ./out --comments false
# Procyon 命令行
java -jar procyon-decompiler.jar -jar target.jar -o ./out
# Vineflower(质量较高,支持新语法)
java -jar vineflower.jar target.jar -dout=./out
```

---



---
📖 本切片 2/2 结束。 本章节结束。