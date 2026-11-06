---
name: ecb-ciphertext-identification
description: >-
  黑盒密文分析四步法：识别 AES/SM4-ECB 加密的数据库字段密文。
  通过块复用模式、共享前缀深度、已知明文对照确认 ECB 模式。
  用户提到密文分析、数据库字段加密、ECB 识别、无源码密文破解时使用。
  来源：cg95306_20260819 实战提炼（62 套 JDBC 密文）。
version: 1.0.0
---

# 黑盒密文分析 — ECB 识别四步法

**前提**：目标在 `config/scope*.json`。
**来源**：案卷 `cg95306_20260819` §sysdatasource 密文实战。

---

## 适用场景

- 数据库字段密文（JDBC URL、密码、API Key）
- 配置文件加密字段
- 无法反编译/无源码时的黑盒分析

## 四步法

### 第一步：编码识别 + 块对齐

```python
import base64

ciphertext = "X4VYOKWzOWX7C8jb0OafEg=="
raw = base64.b64decode(ciphertext)
print(f"长度: {len(raw)} 字节")
print(f"是 16 的倍数: {len(raw) % 16 == 0}")  # AES/SM4
print(f"是 8 的倍数: {len(raw) % 8 == 0}")     # DES/3DES
```

### 第二步：第一块比较

```python
# 收集多条密文（越多越好）
ciphertexts = [base64.b64decode(c) for c in all_ciphertexts]
first_blocks = [c[:16] for c in ciphertexts]
# 如果第一块全部相同 → ECB 或固定 IV 的 CBC
unique_first = len(set(first_blocks))
print(f"第一块种类: {unique_first} / {len(first_blocks)}")
# cg95306: 62/62 相同 → 强 ECB 信号
```

### 第三步：共享前缀深度

```python
# 对比不同明文密文的块级共享
def shared_blocks(c1, c2, block_size=16):
    count = 0
    for i in range(0, min(len(c1), len(c2)), block_size):
        if c1[i:i+block_size] == c2[i:i+block_size]:
            count += 1
        else:
            break
    return count

# ECB: 相同明文前缀 → 相同密文前缀（块级对齐）
# CBC: 即使相同明文，第二块起也因链式不同而不同
# 共享深度 > 1 块的对数越多 → ECB 越确定
```

### 第四步：已知明文验证

```
已知: JDBC URL 以 "jdbc:mysql://10." 开头（16 字节）
对应: 第一块密文应全部相同（因为明文相同 + ECB）
验证: ✅ 62 条全相同 → ECB 确认
```

## 确认后的攻击路径

```
ECB 确认 → 密钥搜索方向:
  1. Actuator /env → 可能有 jasypt/加密配置
  2. heapdump → 内存中的密钥对象
  3. 反编译 JAR → DataSourceBuilder / setPassword 附近
  4. Nacos 配置 → 可能有加密配置
  5. 框架默认密钥（Spring Jasypt、自定义 AES）
```

## 常见框架加密方式

| 框架 | 加密 | 密钥来源 |
|------|------|----------|
| Jasypt | PBE (非 ECB) | `jasypt.encryptor.password` |
| Druid | ConfigTools RSA | 内置/自定义公钥 |
| 自定义 AES-ECB | AES/ECB/PKCS5 | 硬编码/配置文件 |
| SM4-ECB | 国密 | 配置文件/HSM |

## 踩坑

- cg95306: 15 个 AppSecret + 日钥 + SM4 派生，2.6 万次不中。密钥只在服务端分析台
- 不要把业务 AppSecret 当 AES 密钥——来源不同
- ECB 识别是免费的（只需密文），但解密仍需要密钥
