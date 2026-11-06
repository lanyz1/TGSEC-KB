## 15. eKYC与NFC芯片验证绕过

### 15.1 NFC芯片验证原理

> 日本2026年修订《犯罪收益转移防止法》，要求远程开户必须使用NFC读取IC芯片，
> 逐步淘汰照片上传式验证。日本个人番号卡(JPKI)的IC芯片包含加密身份数据，
> 通过NFC读取后与持卡人面部匹配，伪造难度远高于图片。

```bash
# === 电子护照/身份证 NFC芯片结构 ===
# ICAO 9303标准: 电子机读旅行证件(eMRTD)
# 
# 芯片数据组:
# DG1: 机读区(MRZ)数据
# DG2: 面部生物特征(JPEG/JPEG2000)
# DG3: 指纹生物特征(可选)
# DG11: 其他个人信息
# DG13: 其他可选数据
# 
# 安全机制:
# - 被动认证(PA): 验证数据签名
# - 主动认证(AA): 验证芯片真实性
# - 基本访问控制(BAC): MRZ作为密钥
# - 补充访问控制(SAC/PACE): 增强密钥交换
# - 扩展访问控制(EAC): 保护敏感生物特征

# NFC读取电子护照/身份证
# 工具: nfcpy, libnfc, Android NFC Reader

# 读取护照MRZ → 派生BAC密钥 → 读取芯片数据
python3 -c "
import nfc

def on_connect(tag):
    print('Tag connected:', tag)
    # 读取MRZ数据
    # MRZ: 护照底部两行机读文字
    # 从MRZ派生BAC密钥
    return True

clf = nfc.ContactlessFrontend('usb')
clf.connect(rdwr={'on-connect': on_connect})
"
```

### 15.2 NFC验证绕过技术

```python
# === NFC芯片验证绕过 ===

# 1. 芯片数据提取与重放
# 攻击者获取合法证件 → 通过NFC读取芯片数据 → 
# 保存加密数据 → 在攻击时重放

def extract_chip_data():
    """提取电子护照芯片数据"""
    import nfc
    
    chip_data = {
        "dg1_mrz": None,       # 机读区数据
        "dg2_face": None,      # 面部照片
        "dg3_fingerprints": None, # 指纹
        "sod": None,           # 文档安全对象(签名)
        "active_auth_response": None, # 主动认证响应
    }
    # 读取所有数据组
    return chip_data

# 2. 芯片模拟攻击
# 使用可编程NFC卡模拟合法证件
# 工具: Proxmark3, Chameleon Ultra, Flipper Zero

# Proxmark3模拟MIFARE/NFC
# hf mf sim -u <uid>  # 模拟UID
# 将提取的芯片数据写入空白NFC卡

# 3. 中间人攻击(NFC Relay)
# 攻击者A靠近受害者证件 → 攻击者B靠近验证终端
# A读取芯片 → 实时转发给B → B模拟芯片 → 验证终端收到合法响应

# 4. BAC密钥暴力破解
# MRZ的熵有限 → 可暴力破解BAC密钥
# 护照号: 9位数字(10^9)
# 出生日期: 6位数字
# 有效期: 6位数字
# 总熵: 约10^21 → 合理时间内可暴力破解(如果缺少速率限制)

# 5. 芯片无源攻击
# 部分早期芯片未实现主动认证
# 攻击: 提取芯片数据 → 克隆到空白芯片
# 检测: 验证终端应检查主动认证响应

# 6. 软件层面的NFC绕过
# 某些APP的NFC验证仅在客户端进行
# 攻击: Hook NFC读取API → 返回伪造的芯片数据
```

### 15.3 NFC验证安全测试检查点

```markdown
□ [ ] NFC芯片是否实现主动认证(AA)
□ [ ] BAC密钥是否从完整的MRZ派生(非简化版)
□ [ ] 是否验证芯片签名(被动认证PA)
□ [ ] 是否检测芯片克隆
□ [ ] 是否检测NFC中继攻击(时间延迟检测)
□ [ ] NFC读取是否在客户端可信执行环境(TEE)中进行
□ [ ] 是否验证证件有效期
□ [ ] 是否检查证件吊销列表
□ [ ] 芯片数据是否与服务端交叉验证
```

---

